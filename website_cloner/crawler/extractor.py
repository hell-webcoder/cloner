"""
Asset extractor for parsing HTML and extracting asset URLs.

Uses BeautifulSoup for HTML parsing to find all linked resources.
"""

import re
from dataclasses import dataclass, field
from typing import Set, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..utils.log import get_logger
from ..utils.paths import normalize_url, is_same_domain


@dataclass
class ExtractedAssets:
    """Container for extracted assets and links."""
    
    # Internal page links to crawl
    internal_links: Set[str] = field(default_factory=set)
    
    # External links (for reference, not crawled)
    external_links: Set[str] = field(default_factory=set)
    
    # Assets by type
    stylesheets: Set[str] = field(default_factory=set)
    scripts: Set[str] = field(default_factory=set)
    images: Set[str] = field(default_factory=set)
    fonts: Set[str] = field(default_factory=set)
    media: Set[str] = field(default_factory=set)
    other_assets: Set[str] = field(default_factory=set)
    
    def all_assets(self) -> Set[str]:
        """Get all asset URLs combined."""
        return (
            self.stylesheets |
            self.scripts |
            self.images |
            self.fonts |
            self.media |
            self.other_assets
        )


class AssetExtractor:
    """
    Extracts assets and links from HTML content.
    
    Finds all linked resources including images, stylesheets, scripts,
    fonts, and media files.
    """
    
    # CSS url() pattern
    CSS_URL_PATTERN = re.compile(r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)')
    
    # srcset pattern
    SRCSET_PATTERN = re.compile(r'([^\s,]+)\s*(?:\d+[wx])?\s*,?')
    
    def __init__(self, base_url: str):
        """
        Initialize the asset extractor.
        
        Args:
            base_url: Base URL for resolving relative URLs
        """
        self.base_url = base_url
        self.logger = get_logger("extractor")
    
    def extract(self, html: str, page_url: str) -> ExtractedAssets:
        """
        Extract all assets and links from HTML content.
        
        Args:
            html: HTML content to parse
            page_url: URL of the page (for resolving relative URLs)
            
        Returns:
            ExtractedAssets object containing all found resources
        """
        assets = ExtractedAssets()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            # Fallback to html.parser if lxml fails
            soup = BeautifulSoup(html, 'html.parser')
        
        # Extract different types of resources
        self._extract_links(soup, page_url, assets)
        self._extract_stylesheets(soup, page_url, assets)
        self._extract_scripts(soup, page_url, assets)
        self._extract_images(soup, page_url, assets)
        self._extract_media(soup, page_url, assets)
        self._extract_css_urls(soup, page_url, assets)
        self._extract_inline_styles(soup, page_url, assets)
        
        self.logger.debug(
            f"Extracted from {page_url}: "
            f"{len(assets.internal_links)} links, "
            f"{len(assets.all_assets())} assets"
        )
        
        return assets
    
    def _extract_links(
        self,
        soup: BeautifulSoup,
        page_url: str,
        assets: ExtractedAssets
    ) -> None:
        """Extract anchor links from the page."""
        for anchor in soup.find_all('a', href=True):
            href = anchor.get('href', '').strip()
            
            if not href:
                continue
            
            # Skip non-HTTP links
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#', 'data:')):
                continue
            
            # Normalize the URL
            full_url = normalize_url(href, page_url)
            
            if not full_url:
                continue
            
            # Categorize as internal or external
            if is_same_domain(full_url, self.base_url):
                assets.internal_links.add(full_url)
            else:
                assets.external_links.add(full_url)
    
    def _extract_stylesheets(
        self,
        soup: BeautifulSoup,
        page_url: str,
        assets: ExtractedAssets
    ) -> None:
        """Extract stylesheet links."""
        # <link rel="stylesheet"> - check if 'stylesheet' is exactly one of the rel values
        # HTML rel attribute can have multiple space-separated values like "stylesheet preload"
        for link in soup.find_all('link', rel=True):
            rel_value = link.get('rel', [])
            # BeautifulSoup returns rel as a list of individual values when using lxml/html.parser
            # e.g., <link rel="stylesheet preload"> becomes ['stylesheet', 'preload']
            if isinstance(rel_value, list):
                rel_values = [v.lower() for v in rel_value]
            else:
                # Handle edge case where rel might be a string (split on whitespace)
                rel_values = rel_value.lower().split()
            
            # Check for exact match of 'stylesheet' as one of the rel values
            # This is list membership check, so 'stylesheet' != 'prestylesheet'
            if 'stylesheet' in rel_values:
                href = link.get('href', '').strip()
                if href:
                    full_url = normalize_url(href, page_url)
                    if full_url:
                        assets.stylesheets.add(full_url)
        
        # <link rel="preload" as="style">
        for link in soup.find_all('link', rel='preload', attrs={'as': 'style'}):
            href = link.get('href', '').strip()
            if href:
                full_url = normalize_url(href, page_url)
                if full_url:
                    assets.stylesheets.add(full_url)
    
    def _extract_scripts(
        self,
        soup: BeautifulSoup,
        page_url: str,
        assets: ExtractedAssets
    ) -> None:
        """Extract script sources."""
        for script in soup.find_all('script', src=True):
            src = script.get('src', '').strip()
            if src:
                full_url = normalize_url(src, page_url)
                if full_url:
                    assets.scripts.add(full_url)
    
    def _extract_images(
        self,
        soup: BeautifulSoup,
        page_url: str,
        assets: ExtractedAssets
    ) -> None:
        """Extract image sources including srcset."""
        # <img src>
        for img in soup.find_all('img'):
            src = img.get('src', '').strip()
            if src and not src.startswith('data:'):
                full_url = normalize_url(src, page_url)
                if full_url:
                    assets.images.add(full_url)
            
            # srcset attribute
            srcset = img.get('srcset', '').strip()
            if srcset:
                for url in self._parse_srcset(srcset):
                    full_url = normalize_url(url, page_url)
                    if full_url:
                        assets.images.add(full_url)
            
            # data-src (lazy loading)
            data_src = img.get('data-src', '').strip()
            if data_src and not data_src.startswith('data:'):
                full_url = normalize_url(data_src, page_url)
                if full_url:
                    assets.images.add(full_url)
        
        # <source srcset> in <picture>
        for source in soup.find_all('source', srcset=True):
            srcset = source.get('srcset', '').strip()
            if srcset:
                for url in self._parse_srcset(srcset):
                    full_url = normalize_url(url, page_url)
                    if full_url:
                        assets.images.add(full_url)
        
        # Background images in style attributes
        for elem in soup.find_all(style=True):
            style = elem.get('style', '')
            for url in self._extract_urls_from_css(style):
                full_url = normalize_url(url, page_url)
                if full_url:
                    assets.images.add(full_url)
        
        # Favicons and icons
        for link in soup.find_all('link', rel=lambda x: x and 'icon' in str(x).lower()):
            href = link.get('href', '').strip()
            if href:
                full_url = normalize_url(href, page_url)
                if full_url:
                    assets.images.add(full_url)
    
    def _extract_media(
        self,
        soup: BeautifulSoup,
        page_url: str,
        assets: ExtractedAssets
    ) -> None:
        """Extract video and audio sources."""
        # <video src>
        for video in soup.find_all('video'):
            src = video.get('src', '').strip()
            if src:
                full_url = normalize_url(src, page_url)
                if full_url:
                    assets.media.add(full_url)
            
            # poster attribute
            poster = video.get('poster', '').strip()
            if poster:
                full_url = normalize_url(poster, page_url)
                if full_url:
                    assets.images.add(full_url)
        
        # <audio src>
        for audio in soup.find_all('audio'):
            src = audio.get('src', '').strip()
            if src:
                full_url = normalize_url(src, page_url)
                if full_url:
                    assets.media.add(full_url)
        
        # <source> elements
        for source in soup.find_all('source', src=True):
            src = source.get('src', '').strip()
            if src:
                full_url = normalize_url(src, page_url)
                if full_url:
                    assets.media.add(full_url)
        
        # <track> for subtitles
        for track in soup.find_all('track', src=True):
            src = track.get('src', '').strip()
            if src:
                full_url = normalize_url(src, page_url)
                if full_url:
                    assets.other_assets.add(full_url)
    
    def _extract_css_urls(
        self,
        soup: BeautifulSoup,
        page_url: str,
        assets: ExtractedAssets
    ) -> None:
        """Extract URLs from inline <style> tags."""
        for style in soup.find_all('style'):
            if style.string:
                for url in self._extract_urls_from_css(style.string):
                    full_url = normalize_url(url, page_url)
                    if full_url:
                        # Categorize by extension
                        lower_url = full_url.lower()
                        if any(ext in lower_url for ext in ['.woff', '.ttf', '.otf', '.eot']):
                            assets.fonts.add(full_url)
                        elif any(ext in lower_url for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']):
                            assets.images.add(full_url)
                        else:
                            assets.other_assets.add(full_url)
    
    def _extract_inline_styles(
        self,
        soup: BeautifulSoup,
        page_url: str,
        assets: ExtractedAssets
    ) -> None:
        """Extract URLs from inline style attributes."""
        for elem in soup.find_all(style=True):
            style = elem.get('style', '')
            for url in self._extract_urls_from_css(style):
                full_url = normalize_url(url, page_url)
                if full_url:
                    assets.images.add(full_url)
    
    def _parse_srcset(self, srcset: str) -> List[str]:
        """
        Parse srcset attribute and extract URLs.
        
        Args:
            srcset: srcset attribute value
            
        Returns:
            List of URLs from srcset
        """
        urls = []
        for part in srcset.split(','):
            part = part.strip()
            if part:
                # Get the URL (first part before any size descriptor)
                url = part.split()[0] if part.split() else part
                if url and not url.startswith('data:'):
                    urls.append(url)
        return urls
    
    def _extract_urls_from_css(self, css: str) -> List[str]:
        """
        Extract URLs from CSS content (url() references).
        
        Args:
            css: CSS content string
            
        Returns:
            List of URLs found in CSS
        """
        urls = []
        for match in self.CSS_URL_PATTERN.finditer(css):
            url = match.group(1).strip()
            if url and not url.startswith('data:'):
                urls.append(url)
        return urls
    
    def extract_css_assets(self, css_content: str, css_url: str) -> Set[str]:
        """
        Extract asset URLs from CSS file content.
        
        Args:
            css_content: CSS file content
            css_url: URL of the CSS file (for resolving relative URLs)
            
        Returns:
            Set of asset URLs found in CSS
        """
        assets = set()
        
        for url in self._extract_urls_from_css(css_content):
            full_url = normalize_url(url, css_url)
            if full_url:
                assets.add(full_url)
        
        # Also look for @import statements
        import_pattern = re.compile(r'@import\s+["\']([^"\']+)["\']|@import\s+url\(["\']?([^"\')\s]+)["\']?\)')
        for match in import_pattern.finditer(css_content):
            url = match.group(1) or match.group(2)
            if url:
                full_url = normalize_url(url, css_url)
                if full_url:
                    assets.add(full_url)
        
        return assets
