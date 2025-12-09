"""
Flask web application for the website cloner.

Provides a web-based UI for controlling the website cloner tool.
"""

import asyncio
import os
import json
import time
import threading
from typing import Dict, Optional
from urllib.parse import urlparse

from flask import Flask, render_template, request, jsonify


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Store for active clone jobs
    app.clone_jobs: Dict[str, dict] = {}
    app.job_counter = 0
    app.job_lock = threading.Lock()
    
    @app.route('/')
    def index():
        """Render the main UI page."""
        return render_template('index.html')
    
    @app.route('/api/clone', methods=['POST'])
    def start_clone():
        """Start a new website clone job."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            url = data.get('url', '').strip()
            if not url:
                return jsonify({'error': 'URL is required'}), 400
            
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url)
            if not parsed.netloc:
                return jsonify({'error': 'Invalid URL format'}), 400
            
            # Get options
            max_pages = int(data.get('maxPages', 200))
            max_depth = int(data.get('maxDepth', 10))
            delay = float(data.get('delay', 0.5))
            respect_robots = data.get('respectRobots', True)
            output_dir = data.get('outputDir', './cloned')
            
            # Validate parameters
            if max_pages < 1 or max_pages > 10000:
                return jsonify({'error': 'Max pages must be between 1 and 10000'}), 400
            if max_depth < 1 or max_depth > 100:
                return jsonify({'error': 'Max depth must be between 1 and 100'}), 400
            if delay < 0 or delay > 60:
                return jsonify({'error': 'Delay must be between 0 and 60 seconds'}), 400
            
            # Create job ID
            with app.job_lock:
                app.job_counter += 1
                job_id = f"job_{app.job_counter}_{int(time.time())}"
            
            # Initialize job status
            app.clone_jobs[job_id] = {
                'id': job_id,
                'url': url,
                'status': 'starting',
                'progress': 0,
                'pages_crawled': 0,
                'assets_downloaded': 0,
                'errors': [],
                'output_dir': os.path.abspath(output_dir),
                'started_at': time.time(),
                'completed_at': None,
                'message': 'Initializing...'
            }
            
            # Start clone job in background thread
            thread = threading.Thread(
                target=_run_clone_job,
                args=(app, job_id, url, output_dir, max_pages, max_depth, delay, respect_robots),
                daemon=True
            )
            thread.start()
            
            return jsonify({
                'jobId': job_id,
                'message': 'Clone job started',
                'status': 'starting'
            })
            
        except ValueError as e:
            return jsonify({'error': f'Invalid parameter value: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to start clone: {str(e)}'}), 500
    
    @app.route('/api/status/<job_id>')
    def get_status(job_id):
        """Get the status of a clone job."""
        job = app.clone_jobs.get(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        return jsonify(job)
    
    @app.route('/api/jobs')
    def list_jobs():
        """List all clone jobs."""
        jobs = list(app.clone_jobs.values())
        jobs.sort(key=lambda x: x.get('started_at', 0), reverse=True)
        return jsonify({'jobs': jobs})
    
    @app.route('/api/cancel/<job_id>', methods=['POST'])
    def cancel_job(job_id):
        """Cancel a running clone job."""
        job = app.clone_jobs.get(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        if job['status'] in ('completed', 'failed', 'cancelled'):
            return jsonify({'error': 'Job is not running'}), 400
        
        job['status'] = 'cancelled'
        job['message'] = 'Job cancelled by user'
        job['completed_at'] = time.time()
        
        return jsonify({'message': 'Job cancelled'})
    
    return app


def _run_clone_job(app, job_id: str, url: str, output_dir: str,
                   max_pages: int, max_depth: int, delay: float,
                   respect_robots: bool):
    """Run a clone job in a background thread."""
    # Import here to avoid circular imports
    from ..crawler import WebsiteCrawler
    
    job = app.clone_jobs[job_id]
    
    try:
        job['status'] = 'running'
        job['message'] = 'Creating crawler...'
        
        # Create crawler
        crawler = WebsiteCrawler(
            url=url,
            output_dir=output_dir,
            max_pages=max_pages,
            max_depth=max_depth,
            delay=delay,
            respect_robots=respect_robots,
            timeout=30000,
            concurrency=10,
            headless=True
        )
        
        # Store crawler reference for potential cancellation
        job['_crawler'] = crawler
        job['message'] = 'Starting crawl...'
        
        # Run the crawler in async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run crawl with progress tracking
            result = loop.run_until_complete(
                _run_crawl_with_progress(crawler, job, app)
            )
            
            # Update final status
            if job['status'] == 'cancelled':
                return
            
            job['status'] = 'completed'
            job['pages_crawled'] = result.pages_crawled
            job['assets_downloaded'] = result.assets_downloaded
            job['errors'] = result.errors[:100]  # Limit errors stored
            job['message'] = f'Completed: {result.pages_crawled} pages, {result.assets_downloaded} assets'
            job['completed_at'] = time.time()
            
        finally:
            loop.close()
            
    except Exception as e:
        job['status'] = 'failed'
        job['message'] = f'Error: {str(e)}'
        job['completed_at'] = time.time()
        job['errors'].append({'error': str(e), 'type': 'job_error'})
    
    finally:
        # Clean up crawler reference
        if '_crawler' in job:
            del job['_crawler']


async def _run_crawl_with_progress(crawler, job, app):
    """Run the crawl and update progress periodically."""
    from ..utils.paths import create_output_structure
    from ..crawler.crawler import CrawlResult
    
    def create_result():
        """Create a CrawlResult from current crawler state."""
        return CrawlResult(
            pages_crawled=len(crawler._visited_urls),
            assets_downloaded=len(crawler.downloader.downloaded_assets),
            errors=crawler._errors,
            sitemap=list(crawler._visited_urls),
            duration_seconds=time.time() - job['started_at']
        )
    
    # Create output directory
    create_output_structure(crawler.output_dir)
    
    # Load robots.txt
    if crawler.respect_robots:
        job['message'] = 'Loading robots.txt...'
        await crawler.robots.load()
        crawler.delay = max(crawler.delay, crawler.robots.get_crawl_delay(crawler.delay))
    
    try:
        # Start renderer
        job['message'] = 'Starting browser...'
        await crawler.renderer.start()
        
        # Crawl pages
        job['message'] = 'Crawling pages...'
        await _crawl_pages_with_progress(crawler, job)
        
        if job['status'] == 'cancelled':
            return create_result()
        
        # Download assets
        job['message'] = 'Downloading assets...'
        await crawler._download_all_assets()
        
        if job['status'] == 'cancelled':
            return create_result()
        
        # Rewrite links
        job['message'] = 'Rewriting links...'
        await crawler._rewrite_all_pages()
        
        # Generate output files
        job['message'] = 'Generating sitemap...'
        crawler._generate_sitemap()
        crawler._generate_error_log()
        
    finally:
        await crawler.renderer.stop()
    
    return create_result()


async def _crawl_pages_with_progress(crawler, job):
    """Crawl pages with progress updates."""
    from collections import deque
    
    queue = deque([(crawler.start_url, 0)])
    crawler._queued_urls.add(crawler.start_url)
    
    while queue and len(crawler._visited_urls) < crawler.max_pages:
        # Check for cancellation
        if job['status'] == 'cancelled':
            return
        
        url, depth = queue.popleft()
        
        if url in crawler._visited_urls:
            continue
        
        if depth > crawler.max_depth:
            continue
        
        if crawler.respect_robots and not crawler.robots.is_allowed(url):
            continue
        
        # Crawl the page
        success = await crawler._crawl_page(url, depth)
        
        # Update progress
        job['pages_crawled'] = len(crawler._visited_urls)
        progress = (len(crawler._visited_urls) / crawler.max_pages) * 100
        job['progress'] = min(progress, 100)
        job['message'] = f'Crawling: {len(crawler._visited_urls)}/{crawler.max_pages} pages'
        
        if success and url in crawler._page_data:
            assets = crawler._page_data[url].get('extracted_assets')
            if assets:
                for link in assets.internal_links:
                    if link not in crawler._visited_urls and link not in crawler._queued_urls:
                        if len(crawler._queued_urls) < crawler.max_pages * 2:
                            queue.append((link, depth + 1))
                            crawler._queued_urls.add(link)
        
        await asyncio.sleep(crawler.delay)


def run_app(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """Run the Flask web application."""
    app = create_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_app()
