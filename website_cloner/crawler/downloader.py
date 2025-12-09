"""
Asset downloader for fetching and saving website resources.

Uses aiohttp for parallel asynchronous downloads.
"""

import asyncio
import os
from typing import Dict, Set, Optional, Tuple
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientTimeout, ClientError

from ..utils.log import get_logger
from ..utils.paths import get_asset_path, get_asset_type, ensure_parent_dir


class AssetDownloader:
    """
    Downloads website assets asynchronously.
    
    Handles parallel downloads with rate limiting and error handling.
    """
    
    # Reasonable timeout for asset downloads
    DEFAULT_TIMEOUT = 30
    
    # Maximum concurrent downloads
    DEFAULT_CONCURRENCY = 10
    
    # User agent for requests
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def __init__(
        self,
        output_dir: str,
        timeout: int = DEFAULT_TIMEOUT,
        concurrency: int = DEFAULT_CONCURRENCY,
        user_agent: str = DEFAULT_USER_AGENT
    ):
        """
        Initialize the asset downloader.
        
        Args:
            output_dir: Base output directory for saving assets
            timeout: Request timeout in seconds
            concurrency: Maximum concurrent downloads
            user_agent: User agent string for requests
        """
        self.output_dir = output_dir
        self.timeout = ClientTimeout(total=timeout)
        self.concurrency = concurrency
        self.user_agent = user_agent
        self.logger = get_logger("downloader")
        
        # Track downloaded assets
        self._downloaded: Dict[str, str] = {}  # URL -> local path
        self._failed: Set[str] = set()
        
        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(concurrency)
    
    @property
    def downloaded_assets(self) -> Dict[str, str]:
        """Get mapping of URL to local path for downloaded assets."""
        return self._downloaded.copy()
    
    @property
    def failed_assets(self) -> Set[str]:
        """Get set of URLs that failed to download."""
        return self._failed.copy()
    
    async def download_assets(
        self,
        urls: Set[str],
        css_callback=None
    ) -> Dict[str, str]:
        """
        Download multiple assets in parallel.
        
        Args:
            urls: Set of asset URLs to download
            css_callback: Optional callback for processing CSS content
                         (for extracting additional assets)
            
        Returns:
            Dictionary mapping URLs to local file paths
        """
        if not urls:
            return {}
        
        self.logger.info(f"Downloading {len(urls)} assets...")
        
        # Create download tasks
        async with aiohttp.ClientSession(
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent}
        ) as session:
            tasks = [
                self._download_asset(session, url, css_callback)
                for url in urls
            ]
            
            # Run all downloads with progress tracking
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for url, result in zip(urls, results):
                if isinstance(result, Exception):
                    self.logger.debug(f"Download failed for {url}: {result}")
                    self._failed.add(url)
        
        self.logger.info(
            f"Downloaded {len(self._downloaded)} assets, "
            f"{len(self._failed)} failed"
        )
        
        return self._downloaded
    
    async def _download_asset(
        self,
        session: aiohttp.ClientSession,
        url: str,
        css_callback=None
    ) -> Optional[str]:
        """
        Download a single asset.
        
        Args:
            session: aiohttp session
            url: Asset URL to download
            css_callback: Optional callback for CSS processing
            
        Returns:
            Local file path if successful, None otherwise
        """
        # Skip if already downloaded
        if url in self._downloaded:
            return self._downloaded[url]
        
        async with self._semaphore:
            try:
                # Determine asset type and local path
                asset_type = get_asset_type(url)
                local_path = get_asset_path(url, asset_type, self.output_dir)
                
                # Ensure directory exists
                ensure_parent_dir(local_path)
                
                # Download the asset
                async with session.get(url, allow_redirects=True) as response:
                    if response.status != 200:
                        self.logger.debug(
                            f"HTTP {response.status} for asset: {url}"
                        )
                        self._failed.add(url)
                        return None
                    
                    content = await response.read()
                    
                    # Process CSS files to find additional assets
                    if css_callback and asset_type == 'css':
                        try:
                            css_text = content.decode('utf-8', errors='ignore')
                            await css_callback(css_text, url)
                        except Exception as e:
                            self.logger.debug(f"CSS callback error: {e}")
                    
                    # Save to file
                    with open(local_path, 'wb') as f:
                        f.write(content)
                    
                    self._downloaded[url] = local_path
                    self.logger.debug(f"Downloaded: {url} -> {local_path}")
                    
                    return local_path
                    
            except ClientError as e:
                self.logger.debug(f"Client error downloading {url}: {e}")
                self._failed.add(url)
                return None
            except asyncio.TimeoutError:
                self.logger.debug(f"Timeout downloading {url}")
                self._failed.add(url)
                return None
            except OSError as e:
                self.logger.debug(f"OS error saving {url}: {e}")
                self._failed.add(url)
                return None
            except Exception as e:
                self.logger.debug(f"Error downloading {url}: {e}")
                self._failed.add(url)
                return None
    
    async def download_page(
        self,
        url: str,
        html_content: str,
        local_path: str
    ) -> bool:
        """
        Save HTML content to a local file.
        
        Args:
            url: Original page URL
            html_content: HTML content to save
            local_path: Local file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            ensure_parent_dir(local_path)
            
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self._downloaded[url] = local_path
            self.logger.debug(f"Saved page: {url} -> {local_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving page {url}: {e}")
            self._failed.add(url)
            return False
    
    def get_local_path(self, url: str) -> Optional[str]:
        """
        Get the local path for a downloaded asset.
        
        Args:
            url: Asset URL
            
        Returns:
            Local file path if downloaded, None otherwise
        """
        return self._downloaded.get(url)
    
    def reset(self) -> None:
        """Reset the downloader state."""
        self._downloaded.clear()
        self._failed.clear()
