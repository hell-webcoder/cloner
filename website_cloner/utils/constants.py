"""
Shared constants for the website cloner.

Contains common configuration values used across multiple modules.
"""

# Default user agent string for all HTTP requests
# Used by both the browser renderer and asset downloader
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Default request timeout in seconds
DEFAULT_TIMEOUT = 30

# Default page load timeout in milliseconds (for Playwright)
DEFAULT_PAGE_TIMEOUT = 30000

# Default concurrent downloads
DEFAULT_CONCURRENCY = 10

# Default crawl delay between requests in seconds
DEFAULT_CRAWL_DELAY = 0.5

# Maximum pages to crawl by default
DEFAULT_MAX_PAGES = 200

# Maximum crawl depth by default
DEFAULT_MAX_DEPTH = 10
