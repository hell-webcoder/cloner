"""
Page renderer using Playwright for JavaScript rendering.

Handles headless browser rendering to capture dynamically generated content.
"""

import asyncio
from typing import Optional, Tuple

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from ..utils.log import get_logger
from ..utils.constants import DEFAULT_USER_AGENT


class PageRenderer:
    """
    Renders web pages using Playwright headless browser.
    
    Captures the final DOM after JavaScript execution.
    """
    
    def __init__(
        self,
        timeout: int = 30000,
        wait_until: str = "networkidle",
        headless: bool = True
    ):
        """
        Initialize the page renderer.
        
        Args:
            timeout: Page load timeout in milliseconds
            wait_until: Event to wait for ('load', 'domcontentloaded', 'networkidle')
            headless: Run browser in headless mode
        """
        self.timeout = timeout
        self.wait_until = wait_until
        self.headless = headless
        self.logger = get_logger("renderer")
        
        self._playwright = None
        self._browser: Optional[Browser] = None
    
    async def start(self) -> None:
        """
        Start the Playwright browser instance.
        """
        self.logger.info("Starting Playwright browser...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        self.logger.info("Browser started successfully")
    
    async def stop(self) -> None:
        """
        Stop the Playwright browser instance.
        """
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self.logger.info("Browser stopped")
    
    async def render_page(
        self,
        url: str,
        user_agent: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Render a page and return the final HTML content.
        
        Args:
            url: URL to render
            user_agent: Optional custom user agent
            
        Returns:
            Tuple of (html_content, final_url) or (None, None) on error
        """
        if not self._browser:
            await self.start()
        
        page: Optional[Page] = None
        
        try:
            # Create new page context
            context = await self._browser.new_context(
                user_agent=user_agent or DEFAULT_USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,
            )
            
            page = await context.new_page()
            
            # Navigate to the URL
            self.logger.debug(f"Rendering: {url}")
            response = await page.goto(
                url,
                wait_until=self.wait_until,
                timeout=self.timeout
            )
            
            if not response:
                self.logger.warning(f"No response for {url}")
                return None, None
            
            if response.status >= 400:
                self.logger.warning(f"HTTP {response.status} for {url}")
                return None, None
            
            # Wait for any additional dynamic content
            await asyncio.sleep(1)
            
            # Get the final URL (after redirects)
            final_url = page.url
            
            # Get the rendered HTML content
            html_content = await page.content()
            
            self.logger.debug(f"Successfully rendered: {final_url}")
            
            return html_content, final_url
            
        except PlaywrightTimeout:
            self.logger.warning(f"Timeout rendering {url}")
            return None, None
        except Exception as e:
            self.logger.error(f"Error rendering {url}: {e}")
            return None, None
        finally:
            if page:
                await page.close()
    
    async def render_page_with_page(
        self,
        url: str,
        user_agent: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[Page]]:
        """
        Render a page and return HTML content and keep page open for screenshots.
        
        Args:
            url: URL to render
            user_agent: Optional custom user agent
            
        Returns:
            Tuple of (html_content, final_url, page) or (None, None, None) on error
            Note: Caller is responsible for closing the page!
        """
        if not self._browser:
            await self.start()
        
        page: Optional[Page] = None
        
        try:
            # Create new page context
            context = await self._browser.new_context(
                user_agent=user_agent or DEFAULT_USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,
            )
            
            page = await context.new_page()
            
            # Navigate to the URL
            self.logger.debug(f"Rendering: {url}")
            response = await page.goto(
                url,
                wait_until=self.wait_until,
                timeout=self.timeout
            )
            
            if not response:
                self.logger.warning(f"No response for {url}")
                if page:
                    await page.close()
                return None, None, None
            
            if response.status >= 400:
                self.logger.warning(f"HTTP {response.status} for {url}")
                if page:
                    await page.close()
                return None, None, None
            
            # Wait for any additional dynamic content
            await asyncio.sleep(1)
            
            # Get the final URL (after redirects)
            final_url = page.url
            
            # Get the rendered HTML content
            html_content = await page.content()
            
            self.logger.debug(f"Successfully rendered: {final_url}")
            
            # Return page open for screenshots
            return html_content, final_url, page
            
        except PlaywrightTimeout:
            self.logger.warning(f"Timeout rendering {url}")
            if page:
                await page.close()
            return None, None, None
        except Exception as e:
            self.logger.error(f"Error rendering {url}: {e}")
            if page:
                await page.close()
            return None, None, None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
