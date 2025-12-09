#!/usr/bin/env python3
"""
Website Cloner - A modern Python-based website cloning tool.

This tool crawls websites, renders JavaScript pages using Playwright,
downloads all assets, and creates offline-viewable copies.

Usage:
    python main.py --url https://example.com --output ./cloned --max-pages 200

Features:
    - Crawls entire websites following internal links
    - Renders JavaScript pages with Playwright
    - Downloads CSS, JS, images, fonts, and media
    - Rewrites links for offline viewing
    - Respects robots.txt
    - Generates sitemap.json
"""

import argparse
import asyncio
import sys
import os

# Add parent directory to path for imports when running as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from website_cloner.crawler import WebsiteCrawler
from website_cloner.utils.log import (
    setup_logger,
    print_status,
    print_success,
    print_error,
    print_info
)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog='website_cloner',
        description='Clone websites for offline viewing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --url https://example.com --output ./cloned
    %(prog)s --url https://example.com --output ./site --max-pages 100 --depth 5
    %(prog)s --url https://example.com -o ./backup --no-robots --delay 1.0

For more information, visit: https://github.com/website-cloner
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--url', '-u',
        type=str,
        required=True,
        help='URL of the website to clone (e.g., https://example.com)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='./cloned',
        help='Output directory for cloned website (default: ./cloned)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--max-pages', '-m',
        type=int,
        default=200,
        help='Maximum number of pages to crawl (default: 200)'
    )
    
    parser.add_argument(
        '--depth', '-d',
        type=int,
        default=10,
        help='Maximum crawl depth (default: 10)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay between requests in seconds (default: 0.5)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30000,
        help='Page load timeout in milliseconds (default: 30000)'
    )
    
    parser.add_argument(
        '--concurrency', '-c',
        type=int,
        default=10,
        help='Maximum concurrent asset downloads (default: 10)'
    )
    
    parser.add_argument(
        '--no-robots',
        action='store_true',
        help='Ignore robots.txt rules'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Run browser in visible mode (useful for debugging)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output except errors'
    )
    
    return parser.parse_args()


def validate_url(url: str) -> str:
    """
    Validate and normalize the input URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        Normalized URL string
        
    Raises:
        ValueError: If URL is invalid
    """
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Basic validation
    from urllib.parse import urlparse
    parsed = urlparse(url)
    
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")
    
    return url


def print_banner() -> None:
    """Print the application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                     WEBSITE CLONER v1.0                       ║
║              Modern Python Website Cloning Tool               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print_status(banner, "bold cyan")


def print_summary(result) -> None:
    """
    Print the crawl summary.
    
    Args:
        result: CrawlResult object
    """
    print("\n" + "=" * 60)
    print_success("CRAWL SUMMARY")
    print("=" * 60)
    print(f"  Pages crawled:     {result.pages_crawled}")
    print(f"  Assets downloaded: {result.assets_downloaded}")
    print(f"  Errors:            {len(result.errors)}")
    print(f"  Duration:          {result.duration_seconds:.1f} seconds")
    print("=" * 60 + "\n")


async def main() -> int:
    """
    Main entry point for the website cloner.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Parse arguments
    args = parse_arguments()
    
    # Set up logging
    import logging
    log_level = logging.DEBUG if args.verbose else (logging.WARNING if args.quiet else logging.INFO)
    setup_logger(level=log_level)
    
    # Print banner
    if not args.quiet:
        print_banner()
    
    try:
        # Validate URL
        url = validate_url(args.url)
        
        # Print configuration
        if not args.quiet:
            print_info(f"Target URL: {url}")
            print_info(f"Output: {args.output}")
            print_info(f"Max pages: {args.max_pages}, Depth: {args.depth}")
        
        # Create crawler
        crawler = WebsiteCrawler(
            url=url,
            output_dir=args.output,
            max_pages=args.max_pages,
            max_depth=args.depth,
            delay=args.delay,
            respect_robots=not args.no_robots,
            timeout=args.timeout,
            concurrency=args.concurrency,
            headless=not args.no_headless
        )
        
        # Run the crawl
        result = await crawler.crawl()
        
        # Print summary
        if not args.quiet:
            print_summary(result)
        
        # Print output location
        print_success(f"Website cloned to: {os.path.abspath(args.output)}")
        
        return 0
        
    except KeyboardInterrupt:
        print_error("\nCrawl interrupted by user")
        return 1
    except ValueError as e:
        print_error(f"Invalid input: {e}")
        return 1
    except Exception as e:
        print_error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def run() -> None:
    """Entry point wrapper for running as module."""
    sys.exit(asyncio.run(main()))


if __name__ == '__main__':
    run()
