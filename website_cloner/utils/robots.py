"""
Robots.txt handler for the website cloner.

Provides parsing and checking of robots.txt rules.
"""

import re
from typing import Set, Optional
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import aiohttp

from .log import get_logger


class RobotsHandler:
    """
    Handler for robots.txt parsing and rule checking.
    
    Respects robots.txt directives to avoid crawling disallowed pages.
    """
    
    def __init__(self, base_url: str, user_agent: str = "*"):
        """
        Initialize the robots.txt handler.
        
        Args:
            base_url: Base URL of the website
            user_agent: User agent string to check rules for
        """
        self.base_url = base_url
        self.user_agent = user_agent
        self.logger = get_logger("robots")
        
        # Parse base URL
        parsed = urlparse(base_url)
        self.robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        # Robot parser
        self.parser = RobotFileParser()
        self.parser.set_url(self.robots_url)
        
        # Cache for allowed/disallowed paths
        self._disallowed_patterns: Set[str] = set()
        self._allowed_patterns: Set[str] = set()
        self._loaded = False
        
        # Crawl delay
        self.crawl_delay: Optional[float] = None
        
        # Sitemaps found
        self.sitemaps: list = []
    
    async def load(self) -> bool:
        """
        Load and parse the robots.txt file.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.robots_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=True
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        self._parse_robots(content)
                        self._loaded = True
                        self.logger.info(f"Loaded robots.txt from {self.robots_url}")
                        return True
                    elif response.status == 404:
                        # No robots.txt means everything is allowed
                        self._loaded = True
                        self.logger.info("No robots.txt found - all URLs allowed")
                        return True
                    else:
                        self.logger.warning(
                            f"Failed to load robots.txt: HTTP {response.status}"
                        )
                        return False
        except aiohttp.ClientError as e:
            self.logger.warning(f"Error fetching robots.txt: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error loading robots.txt: {e}")
            return False
    
    def _parse_robots(self, content: str) -> None:
        """
        Parse robots.txt content manually for more control.
        
        Args:
            content: robots.txt file content
        """
        current_block_applies = False
        reading_user_agents = True  # Track if we're still reading user-agent lines
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse directive
            if ':' in line:
                directive, value = line.split(':', 1)
                directive = directive.strip().lower()
                value = value.strip()
                
                if directive == 'user-agent':
                    if not reading_user_agents:
                        # Starting a new block after non-user-agent directives
                        reading_user_agents = True
                        current_block_applies = False
                    
                    # Check if this user-agent applies to us
                    if value == '*' or value.lower() == self.user_agent.lower():
                        current_block_applies = True
                
                elif directive == 'disallow':
                    reading_user_agents = False
                    if current_block_applies and value:
                        self._disallowed_patterns.add(value)
                
                elif directive == 'allow':
                    reading_user_agents = False
                    if current_block_applies and value:
                        self._allowed_patterns.add(value)
                
                elif directive == 'crawl-delay':
                    reading_user_agents = False
                    if current_block_applies:
                        try:
                            self.crawl_delay = float(value)
                        except ValueError:
                            pass
                
                elif directive == 'sitemap':
                    # Sitemaps are global, not block-specific
                    self.sitemaps.append(value)
        
        # Also use the standard parser as backup
        self.parser.parse(content.split('\n'))
    
    def is_allowed(self, url: str) -> bool:
        """
        Check if a URL is allowed to be crawled.
        
        Args:
            url: URL to check
            
        Returns:
            True if allowed, False if disallowed
        """
        if not self._loaded:
            # If robots.txt wasn't loaded, allow everything
            return True
        
        parsed = urlparse(url)
        path = parsed.path
        
        # Check allow rules first (they take precedence)
        for pattern in self._allowed_patterns:
            if self._matches_pattern(path, pattern):
                return True
        
        # Check disallow rules
        for pattern in self._disallowed_patterns:
            if self._matches_pattern(path, pattern):
                self.logger.debug(f"URL disallowed by robots.txt: {url}")
                return False
        
        # Also check using standard parser
        try:
            if not self.parser.can_fetch(self.user_agent, url):
                return False
        except Exception:
            pass
        
        return True
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """
        Check if a path matches a robots.txt pattern.
        
        Args:
            path: URL path to check
            pattern: robots.txt pattern
            
        Returns:
            True if matches, False otherwise
        """
        if not pattern:
            return False
        
        # Handle wildcard patterns
        if '*' in pattern or '$' in pattern:
            # Convert to regex
            regex_pattern = pattern.replace('*', '.*')
            if regex_pattern.endswith('$'):
                regex_pattern = regex_pattern[:-1] + '$'
            else:
                regex_pattern += '.*'
            try:
                return bool(re.match(regex_pattern, path))
            except re.error:
                return False
        
        # Simple prefix matching
        return path.startswith(pattern)
    
    def get_crawl_delay(self, default: float = 0.5) -> float:
        """
        Get the crawl delay from robots.txt or use default.
        
        Args:
            default: Default delay in seconds
            
        Returns:
            Crawl delay in seconds
        """
        if self.crawl_delay is not None:
            return self.crawl_delay
        return default
