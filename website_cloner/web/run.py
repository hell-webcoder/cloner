#!/usr/bin/env python3
"""
Entry point for running the Website Cloner web UI.

Usage:
    python -m website_cloner.web.run --host 0.0.0.0 --port 5000
"""

import argparse
import sys
import os

# Add parent directory to path for imports when running as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from website_cloner.web.app import run_app


def main():
    """Parse arguments and run the web application."""
    parser = argparse.ArgumentParser(
        description='Run the Website Cloner web UI'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=5000,
        help='Port to listen on (default: 5000)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    args = parser.parse_args()
    
    print(f"Starting Website Cloner Web UI at http://{args.host}:{args.port}")
    run_app(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
