"""
Utility modules for website cloning.

Contains logging, path handling, robots.txt parsing utilities, and constants.
"""

from .log import setup_logger, get_logger
from .paths import normalize_url, get_asset_path, ensure_dir
from .robots import RobotsHandler
from .constants import (
    DEFAULT_USER_AGENT,
    DEFAULT_TIMEOUT,
    DEFAULT_PAGE_TIMEOUT,
    DEFAULT_CONCURRENCY,
    DEFAULT_CRAWL_DELAY,
    DEFAULT_MAX_PAGES,
    DEFAULT_MAX_DEPTH,
)

__all__ = [
    "setup_logger",
    "get_logger",
    "normalize_url",
    "get_asset_path",
    "ensure_dir",
    "RobotsHandler",
    "DEFAULT_USER_AGENT",
    "DEFAULT_TIMEOUT",
    "DEFAULT_PAGE_TIMEOUT",
    "DEFAULT_CONCURRENCY",
    "DEFAULT_CRAWL_DELAY",
    "DEFAULT_MAX_PAGES",
    "DEFAULT_MAX_DEPTH",
]
