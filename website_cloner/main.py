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
    
    # UI Extraction options
    parser.add_argument(
        '--extract-ui',
        action='store_true',
        help='Enable comprehensive UI extraction (colors, typography, components, etc.)'
    )
    
    parser.add_argument(
        '--screenshots',
        action='store_true',
        help='Capture screenshots at multiple viewport sizes'
    )
    
    parser.add_argument(
        '--analyze-accessibility',
        action='store_true',
        help='Run accessibility (WCAG) analysis'
    )
    
    parser.add_argument(
        '--analyze-seo',
        action='store_true',
        help='Run SEO analysis'
    )
    
    parser.add_argument(
        '--analyze-performance',
        action='store_true',
        help='Run performance analysis'
    )
    
    parser.add_argument(
        '--viewports',
        type=str,
        default='mobile,tablet,desktop',
        help='Comma-separated viewport sizes for screenshots (default: mobile,tablet,desktop)'
    )
    
    parser.add_argument(
        '--full-analysis',
        action='store_true',
        help='Enable all analysis features (screenshots, accessibility, SEO, performance)'
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
    
    if result.screenshots_captured > 0:
        print(f"  Screenshots:       {result.screenshots_captured}")
    
    if result.ui_analysis:
        print("")
        print("  UI Analysis:")
        if 'accessibility_score' in result.ui_analysis:
            print(f"    Accessibility Score: {result.ui_analysis['accessibility_score']}/100")
        if 'seo_score' in result.ui_analysis:
            print(f"    SEO Score:          {result.ui_analysis['seo_score']}/100")
        if 'performance_score' in result.ui_analysis:
            print(f"    Performance Score:  {result.ui_analysis['performance_score']}/100")
        if result.ui_analysis.get('colors'):
            print(f"    Colors extracted:   {len(result.ui_analysis['colors'])}")
        if result.ui_analysis.get('fonts'):
            print(f"    Fonts found:        {len(result.ui_analysis['fonts'])}")
    
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
        
        # Determine UI extraction settings
        extract_ui = args.extract_ui or args.full_analysis
        capture_screenshots = args.screenshots or args.full_analysis
        analyze_accessibility = args.analyze_accessibility or args.full_analysis
        analyze_seo = args.analyze_seo or args.full_analysis
        analyze_performance = args.analyze_performance or args.full_analysis
        viewports = args.viewports.split(',') if args.viewports else None
        
        # Print configuration
        if not args.quiet:
            print_info(f"Target URL: {url}")
            print_info(f"Output: {args.output}")
            print_info(f"Max pages: {args.max_pages}, Depth: {args.depth}")
            if extract_ui or capture_screenshots:
                features = []
                if capture_screenshots:
                    features.append("screenshots")
                if extract_ui:
                    features.append("UI extraction")
                if analyze_accessibility:
                    features.append("accessibility")
                if analyze_seo:
                    features.append("SEO")
                if analyze_performance:
                    features.append("performance")
                print_info(f"Analysis features: {', '.join(features)}")
        
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
            headless=not args.no_headless,
            extract_ui=extract_ui,
            capture_screenshots=capture_screenshots,
            analyze_accessibility=analyze_accessibility,
            analyze_seo=analyze_seo,
            analyze_performance=analyze_performance,
            viewports=viewports
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
