# Website Cloner

A modern, Python-based website cloning tool that creates offline copies of websites. Similar to HTTrack but built with modern technologies.

## Features

- 🌐 **Full Website Crawling**: Crawls entire websites following internal links
- 🎭 **JavaScript Rendering**: Uses Playwright to render dynamic content
- 📦 **Asset Downloading**: Downloads CSS, JS, images, fonts, and media files
- 🔗 **Link Rewriting**: Rewrites all URLs for offline viewing
- 🤖 **robots.txt Compliance**: Respects robots.txt rules by default
- 📊 **Sitemap Generation**: Creates sitemap.json of crawled pages
- ⚡ **Async Downloads**: Parallel asset downloading for speed
- 🎨 **Beautiful CLI**: Colorful output with rich (optional)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Install Dependencies

```bash
# Clone the repository
git clone https://github.com/your-username/cloner.git
cd cloner

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browser (required)
playwright install chromium
```

## Usage

### Basic Usage

```bash
# Clone a website
python -m website_cloner.main --url https://example.com --output ./cloned

# Or use the shorthand
python website_cloner/main.py -u https://example.com -o ./cloned
```

### Command Line Options

```
Options:
  --url, -u          URL of website to clone (required)
  --output, -o       Output directory (default: ./cloned)
  --max-pages, -m    Maximum pages to crawl (default: 200)
  --depth, -d        Maximum crawl depth (default: 10)
  --delay            Delay between requests in seconds (default: 0.5)
  --timeout          Page load timeout in ms (default: 30000)
  --concurrency, -c  Max concurrent downloads (default: 10)
  --no-robots        Ignore robots.txt rules
  --no-headless      Show browser window (for debugging)
  --verbose, -v      Enable verbose logging
  --quiet, -q        Suppress output except errors
```

### Examples

```bash
# Clone with custom settings
python -m website_cloner.main --url https://example.com --output ./site --max-pages 100 --depth 5

# Fast crawl (ignore robots.txt, high concurrency)
python -m website_cloner.main --url https://example.com -o ./backup --no-robots --concurrency 20

# Debug mode (visible browser)
python -m website_cloner.main --url https://example.com -o ./debug --no-headless --verbose
```

## Output Structure

```
output/
├── index.html              # Homepage
├── page1.html              # Other pages
├── about/
│   └── index.html
├── assets/
│   ├── css/               # Stylesheets
│   ├── js/                # JavaScript files
│   ├── images/            # Images (PNG, JPG, SVG, etc.)
│   ├── fonts/             # Web fonts
│   └── media/             # Video/audio files
├── sitemap.json           # List of crawled URLs
└── errors.json            # Failed downloads (if any)
```

## Project Structure

```
website_cloner/
├── __init__.py
├── main.py                 # CLI entry point
├── crawler/
│   ├── __init__.py
│   ├── crawler.py          # Main crawling orchestrator
│   ├── renderer.py         # Playwright page rendering
│   ├── extractor.py        # HTML parsing & asset extraction
│   ├── downloader.py       # Async asset downloading
│   └── rewrite.py          # Link rewriting for offline use
└── utils/
    ├── __init__.py
    ├── log.py              # Logging utilities
    ├── paths.py            # URL/path helpers
    └── robots.py           # robots.txt handling
```

## How It Works

1. **Crawling**: Starting from the given URL, the crawler visits all internal links using BFS
2. **Rendering**: Each page is loaded in Playwright to execute JavaScript and capture the final DOM
3. **Extraction**: BeautifulSoup parses the HTML to find all linked resources
4. **Downloading**: Assets are downloaded in parallel using aiohttp
5. **Rewriting**: All URLs in HTML and CSS are rewritten to relative paths
6. **Saving**: Pages and assets are saved in an organized directory structure

## Technical Details

- **JavaScript Rendering**: Uses Playwright with Chromium for full JS execution
- **Rate Limiting**: Configurable delay between requests (default: 0.5s)
- **robots.txt**: Parses and respects Disallow/Allow directives
- **Asset Types**: Handles CSS, JS, images, fonts, video, audio, and more
- **URL Handling**: Supports absolute, relative, and protocol-relative URLs
- **Error Handling**: Graceful handling of failed downloads with error logging

## Dependencies

- **playwright**: Headless browser automation
- **beautifulsoup4**: HTML parsing
- **lxml**: Fast HTML/XML parser
- **aiohttp**: Async HTTP client
- **rich**: Beautiful terminal output (optional)

## Legal Notice

⚠️ **Important**: This tool is intended for legitimate purposes such as:
- Creating offline backups of your own websites
- Archiving publicly available content
- Research and educational purposes

Always respect:
- Website terms of service
- Copyright laws
- robots.txt directives
- Rate limiting to avoid server overload

Do not use this tool to:
- Clone websites without permission
- Violate copyright or intellectual property rights
- Overload or disrupt web servers

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
