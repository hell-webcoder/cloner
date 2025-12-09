"""
Link rewriter for converting URLs to local relative paths.

Rewrites all references in HTML to point to locally downloaded assets.
"""

import os
import re
from typing import Dict, Optional
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup

from ..utils.log import get_logger
from ..utils.paths import get_relative_path, normalize_url


class LinkRewriter:
    """
    Rewrites URLs in HTML content to local relative paths.
    
    Converts all asset references and internal links to work offline.
    """
    
    # CSS url() pattern for replacement
    CSS_URL_PATTERN = re.compile(r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)')
    
    def __init__(self, base_url: str, output_dir: str):
        """
        Initialize the link rewriter.
        
        Args:
            base_url: Base URL of the website
            output_dir: Base output directory
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.logger = get_logger("rewriter")
    
    def rewrite_html(
        self,
        html: str,
        page_url: str,
        page_local_path: str,
        url_mapping: Dict[str, str]
    ) -> str:
        """
        Rewrite all URLs in HTML content to local paths.
        
        Args:
            html: HTML content to rewrite
            page_url: Original URL of the page
            page_local_path: Local file path where page will be saved
            url_mapping: Dictionary mapping URLs to local paths
            
        Returns:
            Rewritten HTML content
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        
        # Rewrite various element attributes
        self._rewrite_links(soup, page_url, page_local_path, url_mapping)
        self._rewrite_stylesheets(soup, page_url, page_local_path, url_mapping)
        self._rewrite_scripts(soup, page_url, page_local_path, url_mapping)
        self._rewrite_images(soup, page_url, page_local_path, url_mapping)
        self._rewrite_media(soup, page_url, page_local_path, url_mapping)
        self._rewrite_inline_styles(soup, page_url, page_local_path, url_mapping)
        self._rewrite_style_tags(soup, page_url, page_local_path, url_mapping)
        
        # Remove base tag to prevent issues
        for base in soup.find_all('base'):
            base.decompose()
        
        return str(soup)
    
    def _get_relative_url(
        self,
        url: str,
        page_url: str,
        page_local_path: str,
        url_mapping: Dict[str, str]
    ) -> Optional[str]:
        """
        Get the relative URL for a resource.
        
        Args:
            url: Original URL
            page_url: URL of the page containing the reference
            page_local_path: Local path of the page
            url_mapping: URL to local path mapping
            
        Returns:
            Relative path string or None if not found
        """
        # Normalize the URL first
        full_url = normalize_url(url, page_url)
        
        if not full_url:
            return None
        
        # Look up in mapping
        local_path = url_mapping.get(full_url)
        
        if not local_path:
            return None
        
        # Calculate relative path
        rel_path = get_relative_path(page_local_path, local_path)
        
        return rel_path
    
    def _rewrite_links(
        self,
        soup: BeautifulSoup,
        page_url: str,
        page_local_path: str,
        url_mapping: Dict[str, str]
    ) -> None:
        """Rewrite anchor href attributes."""
        for anchor in soup.find_all('a', href=True):
            href = anchor.get('href', '').strip()
            
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'data:')):
                continue
            
            rel_path = self._get_relative_url(href, page_url, page_local_path, url_mapping)
            
            if rel_path:
                anchor['href'] = rel_path
            else:
                # For external links, keep the original URL
                full_url = normalize_url(href, page_url)
                if full_url:
                    anchor['href'] = full_url
    
    def _rewrite_stylesheets(
        self,
        soup: BeautifulSoup,
        page_url: str,
        page_local_path: str,
        url_mapping: Dict[str, str]
    ) -> None:
        """Rewrite stylesheet link href attributes."""
        for link in soup.find_all('link', href=True):
            href = link.get('href', '').strip()
            
            if not href:
                continue
            
            rel_path = self._get_relative_url(href, page_url, page_local_path, url_mapping)
            
            if rel_path:
                link['href'] = rel_path
    
    def _rewrite_scripts(
        self,
        soup: BeautifulSoup,
        page_url: str,
        page_local_path: str,
        url_mapping: Dict[str, str]
    ) -> None:
        """Rewrite script src attributes."""
        for script in soup.find_all('script', src=True):
            src = script.get('src', '').strip()
            
            if not src:
                continue
            
            rel_path = self._get_relative_url(src, page_url, page_local_path, url_mapping)
            
            if rel_path:
                script['src'] = rel_path
    
    def _rewrite_images(
        self,
        soup: BeautifulSoup,
        page_url: str,
        page_local_path: str,
        url_mapping: Dict[str, str]
    ) -> None:
        """Rewrite image src and srcset attributes."""
        for img in soup.find_all('img'):
            # src attribute
            src = img.get('src', '').strip()
            if src and not src.startswith('data:'):
                rel_path = self._get_relative_url(src, page_url, page_local_path, url_mapping)
                if rel_path:
                    img['src'] = rel_path
            
            # srcset attribute
            srcset = img.get('srcset', '').strip()
            if srcset:
                new_srcset = self._rewrite_srcset(srcset, page_url, page_local_path, url_mapping)
                if new_srcset:
                    img['srcset'] = new_srcset
            
            # data-src (lazy loading)
            data_src = img.get('data-src', '').strip()
            if data_src and not data_src.startswith('data:'):
                rel_path = self._get_relative_url(data_src, page_url, page_local_path, url_mapping)
                if rel_path:
                    img['data-src'] = rel_path
        
        # Also handle source elements in picture
        for source in soup.find_all('source', srcset=True):
            srcset = source.get('srcset', '').strip()
            if srcset:
                new_srcset = self._rewrite_srcset(srcset, page_url, page_local_path, url_mapping)
                if new_srcset:
                    source['srcset'] = new_srcset
        
        # Icons and favicons
        for link in soup.find_all('link', href=True):
            rel = link.get('rel', [])
            if isinstance(rel, list):
                rel = ' '.join(rel)
            
            if 'icon' in rel.lower():
                href = link.get('href', '').strip()
                if href:
                    rel_path = self._get_relative_url(href, page_url, page_local_path, url_mapping)
                    if rel_path:
                        link['href'] = rel_path
    
    def _rewrite_media(
        self,
        soup: BeautifulSoup,
        page_url: str,
        page_local_path: str,
        url_mapping: Dict[str, str]
    ) -> None:
        """Rewrite video and audio sources."""
        # Video elements
        for video in soup.find_all('video'):
            src = video.get('src', '').strip()
            if src:
                rel_path = self._get_relative_url(src, page_url, page_local_path, url_mapping)
                if rel_path:
                    video['src'] = rel_path
            
            poster = video.get('poster', '').strip()
            if poster:
                rel_path = self._get_relative_url(poster, page_url, page_local_path, url_mapping)
                if rel_path:
                    video['poster'] = rel_path
        
        # Audio elements
        for audio in soup.find_all('audio'):
            src = audio.get('src', '').strip()
            if src:
                rel_path = self._get_relative_url(src, page_url, page_local_path, url_mapping)
                if rel_path:
                    audio['src'] = rel_path
        
        # Source elements
        for source in soup.find_all('source', src=True):
            src = source.get('src', '').strip()
            if src:
                rel_path = self._get_relative_url(src, page_url, page_local_path, url_mapping)
                if rel_path:
                    source['src'] = rel_path
        
        # Track elements
        for track in soup.find_all('track', src=True):
            src = track.get('src', '').strip()
            if src:
                rel_path = self._get_relative_url(src, page_url, page_local_path, url_mapping)
                if rel_path:
                    track['src'] = rel_path
    
    def _rewrite_inline_styles(
        self,
        soup: BeautifulSoup,
        page_url: str,
        page_local_path: str,
        url_mapping: Dict[str, str]
    ) -> None:
        """Rewrite URLs in inline style attributes."""
        for elem in soup.find_all(style=True):
            style = elem.get('style', '')
            new_style = self._rewrite_css_urls(style, page_url, page_local_path, url_mapping)
            if new_style != style:
                elem['style'] = new_style
    
    def _rewrite_style_tags(
        self,
        soup: BeautifulSoup,
        page_url: str,
        page_local_path: str,
        url_mapping: Dict[str, str]
    ) -> None:
        """Rewrite URLs in <style> tags."""
        for style in soup.find_all('style'):
            if style.string:
                new_css = self._rewrite_css_urls(
                    style.string, page_url, page_local_path, url_mapping
                )
                style.string = new_css
    
    def _rewrite_srcset(
        self,
        srcset: str,
        page_url: str,
        page_local_path: str,
        url_mapping: Dict[str, str]
    ) -> str:
        """
        Rewrite URLs in srcset attribute.
        
        Args:
            srcset: Original srcset value
            page_url: URL of the page
            page_local_path: Local path of the page
            url_mapping: URL to local path mapping
            
        Returns:
            Rewritten srcset string
        """
        new_parts = []
        
        for part in srcset.split(','):
            part = part.strip()
            if not part:
                continue
            
            parts = part.split()
            if parts:
                url = parts[0]
                descriptor = ' '.join(parts[1:]) if len(parts) > 1 else ''
                
                if not url.startswith('data:'):
                    rel_path = self._get_relative_url(url, page_url, page_local_path, url_mapping)
                    if rel_path:
                        url = rel_path
                
                if descriptor:
                    new_parts.append(f"{url} {descriptor}")
                else:
                    new_parts.append(url)
        
        return ', '.join(new_parts)
    
    def _rewrite_css_urls(
        self,
        css: str,
        page_url: str,
        page_local_path: str,
        url_mapping: Dict[str, str]
    ) -> str:
        """
        Rewrite url() references in CSS.
        
        Args:
            css: CSS content
            page_url: URL context for resolving relative URLs
            page_local_path: Local path of the containing file
            url_mapping: URL to local path mapping
            
        Returns:
            CSS with rewritten URLs
        """
        def replace_url(match):
            url = match.group(1).strip()
            
            if url.startswith('data:'):
                return match.group(0)
            
            rel_path = self._get_relative_url(url, page_url, page_local_path, url_mapping)
            
            if rel_path:
                return f'url("{rel_path}")'
            
            return match.group(0)
        
        return self.CSS_URL_PATTERN.sub(replace_url, css)
    
    def rewrite_css_file(
        self,
        css_content: str,
        css_url: str,
        css_local_path: str,
        url_mapping: Dict[str, str]
    ) -> str:
        """
        Rewrite URLs in a CSS file.
        
        Args:
            css_content: CSS file content
            css_url: Original URL of the CSS file
            css_local_path: Local path of the CSS file
            url_mapping: URL to local path mapping
            
        Returns:
            Rewritten CSS content
        """
        return self._rewrite_css_urls(css_content, css_url, css_local_path, url_mapping)
