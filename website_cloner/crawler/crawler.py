"""
Main website crawler module.

Orchestrates the crawling process including page rendering, asset extraction,
downloading, and link rewriting.
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional
from urllib.parse import urlparse

from .renderer import PageRenderer
from .extractor import AssetExtractor, ExtractedAssets
from .downloader import AssetDownloader
from .rewrite import LinkRewriter
from ..utils.log import get_logger, print_status, print_success, print_error, print_info
from ..utils.paths import (
    normalize_url,
    url_to_path,
    create_output_structure,
    is_same_domain,
    get_domain
)
from ..utils.robots import RobotsHandler


@dataclass
class CrawlResult:
    """Results of the crawling operation."""
    
    pages_crawled: int = 0
    assets_downloaded: int = 0
    errors: List[Dict] = field(default_factory=list)
    sitemap: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class WebsiteCrawler:
    """
    Main website crawler class.
    
    Coordinates all components to crawl and clone a website.
    """
    
    def __init__(
        self,
        url: str,
        output_dir: str,
        max_pages: int = 200,
        max_depth: int = 10,
        delay: float = 0.5,
        respect_robots: bool = True,
        timeout: int = 30000,
        concurrency: int = 10,
        headless: bool = True
    ):
        """
        Initialize the website crawler.
        
        Args:
            url: Starting URL to crawl
            output_dir: Directory to save cloned website
            max_pages: Maximum number of pages to crawl
            max_depth: Maximum crawl depth from starting URL
            delay: Delay between requests in seconds
            respect_robots: Whether to respect robots.txt
            timeout: Page load timeout in milliseconds
            concurrency: Maximum concurrent asset downloads
            headless: Run browser in headless mode
        """
        self.start_url = normalize_url(url)
        self.output_dir = os.path.abspath(output_dir)
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.delay = delay
        self.respect_robots = respect_robots
        self.timeout = timeout
        self.concurrency = concurrency
        self.headless = headless
        
        # Extract domain for same-domain checking
        self.domain = get_domain(self.start_url)
        
        # Initialize logger
        self.logger = get_logger("crawler")
        
        # Initialize components
        self.renderer = PageRenderer(timeout=timeout, headless=headless)
        self.extractor = AssetExtractor(self.start_url)
        self.downloader = AssetDownloader(
            output_dir=self.output_dir,
            concurrency=concurrency
        )
        self.rewriter = LinkRewriter(self.start_url, self.output_dir)
        self.robots = RobotsHandler(self.start_url)
        
        # Tracking sets
        self._visited_urls: Set[str] = set()
        self._queued_urls: Set[str] = set()
        self._all_assets: Set[str] = set()
        self._page_data: Dict[str, Dict] = {}  # URL -> {html, local_path, assets}
        self._errors: List[Dict] = []
        
        # URL to local path mapping for rewriting
        self._url_mapping: Dict[str, str] = {}
    
    async def crawl(self) -> CrawlResult:
        """
        Start the website crawling process.
        
        Returns:
            CrawlResult with statistics and information
        """
        start_time = time.time()
        
        print_info(f"Starting crawl of {self.start_url}")
        print_info(f"Output directory: {self.output_dir}")
        print_info(f"Max pages: {self.max_pages}, Max depth: {self.max_depth}")
        
        # Create output directory structure
        create_output_structure(self.output_dir)
        
        # Load robots.txt
        if self.respect_robots:
            await self.robots.load()
            self.delay = max(self.delay, self.robots.get_crawl_delay(self.delay))
            print_info(f"Crawl delay: {self.delay}s")
        
        try:
            # Start the renderer
            await self.renderer.start()
            
            # Crawl pages using BFS
            await self._crawl_pages()
            
            # Download all discovered assets
            await self._download_all_assets()
            
            # Rewrite links in all pages
            await self._rewrite_all_pages()
            
            # Generate sitemap and error files
            self._generate_sitemap()
            self._generate_error_log()
            
        finally:
            # Stop the renderer
            await self.renderer.stop()
        
        duration = time.time() - start_time
        
        result = CrawlResult(
            pages_crawled=len(self._visited_urls),
            assets_downloaded=len(self.downloader.downloaded_assets),
            errors=self._errors,
            sitemap=list(self._visited_urls),
            duration_seconds=duration
        )
        
        print_success(
            f"Crawl complete! {result.pages_crawled} pages, "
            f"{result.assets_downloaded} assets in {duration:.1f}s"
        )
        
        return result
    
    async def _crawl_pages(self) -> None:
        """Crawl all pages using breadth-first search."""
        # Queue: (url, depth)
        queue: List[tuple] = [(self.start_url, 0)]
        self._queued_urls.add(self.start_url)
        
        while queue and len(self._visited_urls) < self.max_pages:
            url, depth = queue.pop(0)
            
            # Skip if already visited
            if url in self._visited_urls:
                continue
            
            # Skip if exceeds max depth
            if depth > self.max_depth:
                continue
            
            # Check robots.txt
            if self.respect_robots and not self.robots.is_allowed(url):
                self.logger.info(f"Skipping (robots.txt): {url}")
                continue
            
            # Crawl the page
            success = await self._crawl_page(url, depth)
            
            if success and url in self._page_data:
                # Add discovered internal links to queue
                assets = self._page_data[url].get('extracted_assets')
                if assets:
                    for link in assets.internal_links:
                        if link not in self._visited_urls and link not in self._queued_urls:
                            if len(self._queued_urls) < self.max_pages * 2:
                                queue.append((link, depth + 1))
                                self._queued_urls.add(link)
            
            # Rate limiting
            await asyncio.sleep(self.delay)
        
        self.logger.info(f"Crawled {len(self._visited_urls)} pages")
    
    async def _crawl_page(self, url: str, depth: int) -> bool:
        """
        Crawl a single page.
        
        Args:
            url: URL to crawl
            depth: Current crawl depth
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"[{len(self._visited_urls) + 1}/{self.max_pages}] Crawling: {url}")
        
        try:
            # Render the page
            html, final_url = await self.renderer.render_page(url)
            
            if not html:
                self._errors.append({
                    'url': url,
                    'error': 'Failed to render page',
                    'type': 'render_error'
                })
                return False
            
            # Use final URL (after redirects) if different
            if final_url and final_url != url:
                # Check if redirected to different domain
                if not is_same_domain(final_url, self.start_url):
                    self.logger.info(f"Skipping external redirect: {final_url}")
                    return False
                url = final_url
            
            # Mark as visited
            self._visited_urls.add(url)
            
            # Extract assets and links
            extracted = self.extractor.extract(html, url)
            
            # Collect all assets
            self._all_assets.update(extracted.stylesheets)
            self._all_assets.update(extracted.scripts)
            self._all_assets.update(extracted.images)
            self._all_assets.update(extracted.fonts)
            self._all_assets.update(extracted.media)
            self._all_assets.update(extracted.other_assets)
            
            # Determine local path for page
            local_path = url_to_path(url, self.output_dir)
            
            # Store page data
            self._page_data[url] = {
                'html': html,
                'local_path': local_path,
                'extracted_assets': extracted,
                'depth': depth
            }
            
            # Add to URL mapping
            self._url_mapping[url] = local_path
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error crawling {url}: {e}")
            self._errors.append({
                'url': url,
                'error': str(e),
                'type': 'crawl_error'
            })
            return False
    
    async def _download_all_assets(self) -> None:
        """Download all discovered assets."""
        if not self._all_assets:
            self.logger.info("No assets to download")
            return
        
        print_info(f"Downloading {len(self._all_assets)} assets...")
        
        # Callback for processing CSS files
        async def css_callback(css_content: str, css_url: str):
            """Extract and queue additional assets from CSS."""
            additional = self.extractor.extract_css_assets(css_content, css_url)
            for asset_url in additional:
                if asset_url not in self._all_assets:
                    self._all_assets.add(asset_url)
        
        # Download assets
        downloaded = await self.downloader.download_assets(
            self._all_assets,
            css_callback=css_callback
        )
        
        # Update URL mapping with asset paths
        self._url_mapping.update(downloaded)
        
        # Log failed downloads
        for url in self.downloader.failed_assets:
            self._errors.append({
                'url': url,
                'error': 'Failed to download asset',
                'type': 'download_error'
            })
    
    async def _rewrite_all_pages(self) -> None:
        """Rewrite links in all crawled pages and save them."""
        print_info(f"Rewriting and saving {len(self._page_data)} pages...")
        
        for url, data in self._page_data.items():
            html = data['html']
            local_path = data['local_path']
            
            try:
                # Rewrite links
                rewritten_html = self.rewriter.rewrite_html(
                    html,
                    url,
                    local_path,
                    self._url_mapping
                )
                
                # Save the page
                await self.downloader.download_page(url, rewritten_html, local_path)
                
            except Exception as e:
                self.logger.error(f"Error saving page {url}: {e}")
                self._errors.append({
                    'url': url,
                    'error': str(e),
                    'type': 'save_error'
                })
        
        # Rewrite CSS files
        await self._rewrite_css_files()
    
    async def _rewrite_css_files(self) -> None:
        """Rewrite URLs in downloaded CSS files."""
        for url, local_path in self._url_mapping.items():
            if local_path.endswith('.css') and os.path.exists(local_path):
                try:
                    with open(local_path, 'r', encoding='utf-8', errors='ignore') as f:
                        css_content = f.read()
                    
                    rewritten_css = self.rewriter.rewrite_css_file(
                        css_content,
                        url,
                        local_path,
                        self._url_mapping
                    )
                    
                    with open(local_path, 'w', encoding='utf-8') as f:
                        f.write(rewritten_css)
                        
                except Exception as e:
                    self.logger.debug(f"Error rewriting CSS {local_path}: {e}")
    
    def _generate_sitemap(self) -> None:
        """Generate sitemap.json file."""
        sitemap_path = os.path.join(self.output_dir, 'sitemap.json')
        
        sitemap_data = {
            'base_url': self.start_url,
            'domain': self.domain,
            'total_pages': len(self._visited_urls),
            'total_assets': len(self.downloader.downloaded_assets),
            'pages': sorted(list(self._visited_urls)),
            'assets': sorted(list(self.downloader.downloaded_assets.keys()))
        }
        
        with open(sitemap_path, 'w', encoding='utf-8') as f:
            json.dump(sitemap_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Generated sitemap: {sitemap_path}")
    
    def _generate_error_log(self) -> None:
        """Generate errors.json file if there are errors."""
        if not self._errors:
            return
        
        errors_path = os.path.join(self.output_dir, 'errors.json')
        
        with open(errors_path, 'w', encoding='utf-8') as f:
            json.dump(self._errors, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Generated error log: {errors_path}")
