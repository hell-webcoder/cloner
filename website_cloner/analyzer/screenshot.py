"""
Screenshot capture module for website UI extraction.

Captures screenshots at multiple viewport sizes and full-page screenshots.
"""

import os
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from playwright.async_api import Page

from ..utils.log import get_logger
from ..utils.paths import ensure_dir


@dataclass
class ViewportSize:
    """Defines a viewport configuration."""
    name: str
    width: int
    height: int
    device_scale_factor: float = 1.0
    is_mobile: bool = False


@dataclass
class ScreenshotResult:
    """Result of screenshot capture for a page."""
    url: str
    screenshots: Dict[str, str] = field(default_factory=dict)  # viewport_name -> file_path
    full_page_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)


# Standard viewport sizes for responsive testing
VIEWPORT_PRESETS = {
    "mobile_small": ViewportSize("mobile_small", 320, 568, is_mobile=True),
    "mobile": ViewportSize("mobile", 375, 667, is_mobile=True),
    "mobile_large": ViewportSize("mobile_large", 414, 896, is_mobile=True),
    "tablet": ViewportSize("tablet", 768, 1024, is_mobile=True),
    "tablet_landscape": ViewportSize("tablet_landscape", 1024, 768, is_mobile=True),
    "laptop": ViewportSize("laptop", 1366, 768),
    "desktop": ViewportSize("desktop", 1920, 1080),
    "desktop_large": ViewportSize("desktop_large", 2560, 1440),
    "4k": ViewportSize("4k", 3840, 2160),
}


class ScreenshotCapture:
    """
    Captures screenshots of web pages at various viewport sizes.
    
    Provides responsive design testing capabilities by capturing
    screenshots at different device sizes.
    """
    
    def __init__(
        self,
        output_dir: str,
        viewports: Optional[List[str]] = None,
        full_page: bool = True,
        generate_thumbnails: bool = True,
        thumbnail_width: int = 300
    ):
        """
        Initialize screenshot capture.
        
        Args:
            output_dir: Directory to save screenshots
            viewports: List of viewport preset names to capture
            full_page: Whether to capture full-page screenshots
            generate_thumbnails: Whether to generate thumbnail images
            thumbnail_width: Width of thumbnail images
        """
        self.output_dir = output_dir
        self.screenshots_dir = os.path.join(output_dir, "screenshots")
        self.full_page = full_page
        self.generate_thumbnails = generate_thumbnails
        self.thumbnail_width = thumbnail_width
        self.logger = get_logger("screenshot")
        
        # Default to common viewports if not specified
        if viewports is None:
            viewports = ["mobile", "tablet", "desktop"]
        
        self.viewports = [
            VIEWPORT_PRESETS.get(v, VIEWPORT_PRESETS["desktop"])
            for v in viewports
            if v in VIEWPORT_PRESETS
        ]
        
        # Ensure output directories exist
        ensure_dir(self.screenshots_dir)
        for viewport in self.viewports:
            ensure_dir(os.path.join(self.screenshots_dir, viewport.name))
        if self.full_page:
            ensure_dir(os.path.join(self.screenshots_dir, "full_page"))
        if self.generate_thumbnails:
            ensure_dir(os.path.join(self.screenshots_dir, "thumbnails"))
    
    async def capture_page(
        self,
        page: Page,
        url: str,
        filename_base: str
    ) -> ScreenshotResult:
        """
        Capture screenshots of a page at all configured viewports.
        
        Args:
            page: Playwright page object
            url: URL of the page
            filename_base: Base filename for screenshots
            
        Returns:
            ScreenshotResult with paths to captured screenshots
        """
        result = ScreenshotResult(url=url)
        
        # Clean filename
        safe_filename = self._sanitize_filename(filename_base)
        
        # Capture at each viewport
        for viewport in self.viewports:
            try:
                screenshot_path = await self._capture_viewport(
                    page, viewport, safe_filename
                )
                result.screenshots[viewport.name] = screenshot_path
            except Exception as e:
                self.logger.error(f"Error capturing {viewport.name}: {e}")
                result.errors.append(f"{viewport.name}: {str(e)}")
        
        # Capture full page at desktop viewport
        if self.full_page:
            try:
                result.full_page_path = await self._capture_full_page(
                    page, safe_filename
                )
            except Exception as e:
                self.logger.error(f"Error capturing full page: {e}")
                result.errors.append(f"full_page: {str(e)}")
        
        # Generate thumbnail
        if self.generate_thumbnails and result.screenshots.get("desktop"):
            try:
                result.thumbnail_path = await self._generate_thumbnail(
                    page, safe_filename
                )
            except Exception as e:
                self.logger.debug(f"Error generating thumbnail: {e}")
        
        return result
    
    async def _capture_viewport(
        self,
        page: Page,
        viewport: ViewportSize,
        filename_base: str
    ) -> str:
        """Capture screenshot at a specific viewport size."""
        # Set viewport
        await page.set_viewport_size({
            "width": viewport.width,
            "height": viewport.height
        })
        
        # Wait for content to reflow
        await asyncio.sleep(0.5)
        
        # Capture screenshot
        filepath = os.path.join(
            self.screenshots_dir,
            viewport.name,
            f"{filename_base}.png"
        )
        
        await page.screenshot(
            path=filepath,
            type="png",
            full_page=False
        )
        
        self.logger.debug(f"Captured {viewport.name}: {filepath}")
        return filepath
    
    async def _capture_full_page(
        self,
        page: Page,
        filename_base: str
    ) -> str:
        """Capture full-page screenshot."""
        # Set to desktop viewport for full page
        await page.set_viewport_size({"width": 1920, "height": 1080})
        await asyncio.sleep(0.5)
        
        filepath = os.path.join(
            self.screenshots_dir,
            "full_page",
            f"{filename_base}_full.png"
        )
        
        await page.screenshot(
            path=filepath,
            type="png",
            full_page=True
        )
        
        self.logger.debug(f"Captured full page: {filepath}")
        return filepath
    
    async def _generate_thumbnail(
        self,
        page: Page,
        filename_base: str
    ) -> str:
        """Generate a small thumbnail image."""
        filepath = os.path.join(
            self.screenshots_dir,
            "thumbnails",
            f"{filename_base}_thumb.png"
        )
        
        # Set to a reasonable viewport
        await page.set_viewport_size({"width": 1200, "height": 800})
        await asyncio.sleep(0.3)
        
        # Capture and let Playwright handle the clipping
        await page.screenshot(
            path=filepath,
            type="png",
            clip={"x": 0, "y": 0, "width": 1200, "height": 800}
        )
        
        return filepath
    
    def _sanitize_filename(self, filename: str) -> str:
        """Convert URL or name to safe filename."""
        import re
        # Remove protocol and www
        filename = re.sub(r'^https?://', '', filename)
        filename = re.sub(r'^www\.', '', filename)
        # Replace unsafe characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        return filename[:100]
    
    async def capture_element(
        self,
        page: Page,
        selector: str,
        filename: str
    ) -> Optional[str]:
        """
        Capture screenshot of a specific element.
        
        Args:
            page: Playwright page object
            selector: CSS selector for the element
            filename: Output filename
            
        Returns:
            Path to screenshot or None if element not found
        """
        try:
            element = await page.query_selector(selector)
            if not element:
                return None
            
            filepath = os.path.join(
                self.screenshots_dir,
                "elements",
                f"{filename}.png"
            )
            ensure_dir(os.path.dirname(filepath))
            
            await element.screenshot(path=filepath)
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error capturing element {selector}: {e}")
            return None
    
    def get_all_viewports(self) -> Dict[str, ViewportSize]:
        """Get all available viewport presets."""
        return VIEWPORT_PRESETS.copy()
