"""
Path and URL utilities for the website cloner.

Provides URL normalization, path generation, and directory management.
"""

import os
import re
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse, urljoin, unquote, quote


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """
    Normalize a URL by resolving relative paths and removing fragments.
    
    Args:
        url: URL to normalize
        base_url: Base URL for resolving relative URLs
        
    Returns:
        Normalized URL string
    """
    # Handle empty or invalid URLs
    if not url or url.startswith(('javascript:', 'data:', 'mailto:', 'tel:', '#')):
        return ""
    
    # Strip whitespace
    url = url.strip()
    
    # Handle protocol-relative URLs
    if url.startswith('//'):
        if base_url:
            parsed_base = urlparse(base_url)
            url = f"{parsed_base.scheme}:{url}"
        else:
            url = f"https:{url}"
    
    # Resolve relative URLs
    if base_url and not url.startswith(('http://', 'https://')):
        url = urljoin(base_url, url)
    
    # Parse and clean the URL
    parsed = urlparse(url)
    
    # Remove fragment
    cleaned = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path or '/',
        parsed.params,
        parsed.query,
        ''  # Remove fragment
    ))
    
    # Remove trailing slash for consistency (except for root path)
    # Check if the path component is not just '/'
    if cleaned.endswith('/') and len(parsed.path) > 1:
        cleaned = cleaned.rstrip('/')
    
    return cleaned


def get_domain(url: str) -> str:
    """
    Extract the domain from a URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain string (e.g., 'example.com')
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()


def is_same_domain(url: str, base_url: str) -> bool:
    """
    Check if a URL belongs to the same domain as the base URL.
    
    Args:
        url: URL to check
        base_url: Base URL for comparison
        
    Returns:
        True if same domain, False otherwise
    """
    url_domain = get_domain(url)
    base_domain = get_domain(base_url)
    
    # Handle www prefix variations
    url_domain = url_domain.replace('www.', '')
    base_domain = base_domain.replace('www.', '')
    
    return url_domain == base_domain


def get_url_path(url: str) -> str:
    """
    Get the path component of a URL.
    
    Args:
        url: URL to extract path from
        
    Returns:
        Path string
    """
    parsed = urlparse(url)
    return parsed.path


def url_to_filename(url: str, default_name: str = "index") -> str:
    """
    Convert a URL to a safe filename.
    
    Args:
        url: URL to convert
        default_name: Default name if URL path is empty
        
    Returns:
        Safe filename string
    """
    parsed = urlparse(url)
    path = unquote(parsed.path).strip('/')
    
    if not path:
        return f"{default_name}.html"
    
    # Replace path separators with underscores for flat structure option
    filename = path.replace('/', '_')
    
    # Remove or replace invalid filename characters
    filename = re.sub(r'[<>:"|?*]', '_', filename)
    
    # Add .html extension if not present
    if not filename.endswith(('.html', '.htm')):
        filename = f"{filename}.html"
    
    return filename


def url_to_path(url: str, output_dir: str) -> str:
    """
    Convert a URL to a local file path preserving directory structure.
    
    Args:
        url: URL to convert
        output_dir: Base output directory
        
    Returns:
        Local file path
    """
    parsed = urlparse(url)
    path = unquote(parsed.path).strip('/')
    
    if not path:
        path = "index.html"
    elif not path.endswith(('.html', '.htm')):
        # Check if it looks like a file with extension
        if '.' not in path.split('/')[-1]:
            path = os.path.join(path, "index.html")
    
    return os.path.join(output_dir, path)


def get_asset_path(url: str, asset_type: str, output_dir: str) -> str:
    """
    Generate a local path for an asset based on its type.
    
    Args:
        url: Asset URL
        asset_type: Type of asset ('css', 'js', 'images', 'fonts', 'media')
        output_dir: Base output directory
        
    Returns:
        Local file path for the asset
    """
    parsed = urlparse(url)
    path = unquote(parsed.path)
    
    # Get filename from URL
    filename = os.path.basename(path) or "asset"
    
    # If filename has no extension, try to determine from URL or add generic
    if '.' not in filename:
        ext_map = {
            'css': '.css',
            'js': '.js',
            'images': '.png',
            'fonts': '.woff2',
            'media': '.mp4'
        }
        filename += ext_map.get(asset_type, '')
    
    # Create unique filename using URL hash to avoid conflicts
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{url_hash}{ext}"
    
    # Sanitize filename
    unique_filename = re.sub(r'[<>:"|?*]', '_', unique_filename)
    
    return os.path.join(output_dir, "assets", asset_type, unique_filename)


def get_asset_type(url: str) -> str:
    """
    Determine the asset type based on URL or file extension.
    
    Args:
        url: Asset URL
        
    Returns:
        Asset type string ('css', 'js', 'images', 'fonts', 'media', or 'other')
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # CSS files
    if path.endswith('.css') or '/css/' in path:
        return 'css'
    
    # JavaScript files
    if path.endswith('.js') or '/js/' in path:
        return 'js'
    
    # Image files
    image_exts = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp', '.avif')
    if path.endswith(image_exts):
        return 'images'
    
    # Font files
    font_exts = ('.woff', '.woff2', '.ttf', '.otf', '.eot')
    if path.endswith(font_exts):
        return 'fonts'
    
    # Media files
    media_exts = ('.mp4', '.webm', '.ogg', '.mp3', '.wav', '.m4a', '.m4v', '.avi', '.mov')
    if path.endswith(media_exts):
        return 'media'
    
    return 'other'


def ensure_dir(path: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path to ensure exists
    """
    os.makedirs(path, exist_ok=True)


def ensure_parent_dir(file_path: str) -> None:
    """
    Ensure the parent directory of a file exists.
    
    Args:
        file_path: File path whose parent directory should exist
    """
    parent = os.path.dirname(file_path)
    if parent:
        ensure_dir(parent)


def create_output_structure(output_dir: str) -> dict:
    """
    Create the output directory structure for cloned website.
    
    Args:
        output_dir: Base output directory
        
    Returns:
        Dictionary of created directory paths
    """
    dirs = {
        'root': output_dir,
        'css': os.path.join(output_dir, 'assets', 'css'),
        'js': os.path.join(output_dir, 'assets', 'js'),
        'images': os.path.join(output_dir, 'assets', 'images'),
        'fonts': os.path.join(output_dir, 'assets', 'fonts'),
        'media': os.path.join(output_dir, 'assets', 'media'),
        'other': os.path.join(output_dir, 'assets', 'other'),
    }
    
    for dir_path in dirs.values():
        ensure_dir(dir_path)
    
    return dirs


def get_relative_path(from_path: str, to_path: str) -> str:
    """
    Calculate the relative path from one file to another.
    
    Args:
        from_path: Source file path
        to_path: Target file path
        
    Returns:
        Relative path string
    """
    from_dir = os.path.dirname(from_path)
    rel_path = os.path.relpath(to_path, from_dir)
    # Use forward slashes for URLs
    return rel_path.replace('\\', '/')
