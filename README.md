# Website Cloner Pro

A modern, comprehensive Python-based website cloning and UI extraction tool. Clone websites for offline viewing and extract design systems, color palettes, typography, accessibility reports, SEO metadata, and more.

![Website Cloner Pro UI](https://github.com/user-attachments/assets/22c29c75-7fd6-499a-9ffb-ef1e992055da)

## Features

### Core Cloning Features
- 🌐 **Full Website Crawling**: Crawls entire websites following internal links
- 🎭 **JavaScript Rendering**: Uses Playwright to render dynamic content
- 📦 **Asset Downloading**: Downloads CSS, JS, images, fonts, and media files
- 🔗 **Link Rewriting**: Rewrites all URLs for offline viewing
- 🤖 **robots.txt Compliance**: Respects robots.txt rules by default
- 📊 **Sitemap Generation**: Creates sitemap.json of crawled pages
- ⚡ **Async Downloads**: Parallel asset downloading for speed
- 🎨 **Beautiful CLI**: Colorful output with rich (optional)
- 🖥️ **Modern Web UI**: Beautiful browser-based interface with dark mode support

### UI Extraction Features
- 📸 **Responsive Screenshots**: Capture pages at mobile, tablet, and desktop viewports
- 🎨 **Color Palette Extraction**: Extract colors and generate CSS custom properties
- 🔤 **Typography Analysis**: Identify fonts, sizes, weights, and build type scales
- 🧩 **Component Detection**: Detect UI components (nav, cards, forms, buttons, etc.)
- 🎯 **CSS Variable Extraction**: Extract and categorize design tokens
- ♿ **Accessibility Analysis**: WCAG compliance checking with detailed reports
- 🔍 **SEO Analysis**: Meta tags, Open Graph, structured data extraction
- 📝 **Form Detection**: Identify and extract form structures
- ⚡ **Performance Analysis**: Resource counting and optimization suggestions
- 📋 **Design System Export**: Generate CSS files with extracted design tokens

## Quick Start (One-Click Setup)

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Option 1: One-Click Setup Script (Recommended)

**Linux/macOS:**
```bash
# Clone the repository
git clone https://github.com/hell-webcoder/cloner.git
cd cloner

# Run the one-click setup script
chmod +x setup.sh
./setup.sh
```

**Windows:**
```batch
# Clone the repository
git clone https://github.com/hell-webcoder/cloner.git
cd cloner

# Run the setup batch file
setup.bat
```

### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/hell-webcoder/cloner.git
cd cloner

# Install the package with all dependencies
pip install -e .

# Install Playwright browser (required)
playwright install chromium
```

### Option 3: Using pip (requirements.txt)

```bash
# Clone the repository
git clone https://github.com/hell-webcoder/cloner.git
cd cloner

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browser (required)
playwright install chromium
```

## Usage

### Web UI (Recommended)

The easiest way to use Website Cloner is through the beautiful web interface:

```bash
# Start the web UI (after installation)
website-cloner-web

# Or with custom host and port
website-cloner-web --host 0.0.0.0 --port 8080
```

Alternative method:
```bash
# Start the web UI
python -m website_cloner.web.run

# Or specify host and port
python -m website_cloner.web.run --host 0.0.0.0 --port 8080
```

Then open your browser at `http://localhost:5000` to access the web interface.

### Command Line Interface

For advanced users, the CLI is also available:

#### Basic Usage

```bash
# Clone a website (after installation)
website-cloner --url https://example.com --output ./cloned

# Or use the module directly
python -m website_cloner.main --url https://example.com --output ./cloned
```

### Command Line Options

```
Basic Options:
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

UI Extraction Options:
  --extract-ui       Enable comprehensive UI extraction
  --screenshots      Capture screenshots at multiple viewport sizes
  --analyze-accessibility  Run WCAG accessibility analysis
  --analyze-seo      Run SEO analysis
  --analyze-performance  Run performance analysis
  --viewports        Comma-separated viewport sizes (default: mobile,tablet,desktop)
  --full-analysis    Enable all analysis features
```

### Examples

```bash
# Clone with custom settings
python -m website_cloner.main --url https://example.com --output ./site --max-pages 100 --depth 5

# Fast crawl (ignore robots.txt, high concurrency)
python -m website_cloner.main --url https://example.com -o ./backup --no-robots --concurrency 20

# Debug mode (visible browser)
python -m website_cloner.main --url https://example.com -o ./debug --no-headless --verbose

# Full UI analysis with screenshots
python -m website_cloner.main --url https://example.com -o ./analyzed --full-analysis

# Clone with specific analysis features
python -m website_cloner.main --url https://example.com -o ./site --screenshots --analyze-accessibility

# Extract design system
python -m website_cloner.main --url https://example.com -o ./design --extract-ui --viewports mobile,desktop
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
├── screenshots/           # (when --screenshots enabled)
│   ├── mobile/            # Mobile viewport screenshots
│   ├── tablet/            # Tablet viewport screenshots
│   ├── desktop/           # Desktop viewport screenshots
│   ├── full_page/         # Full page screenshots
│   └── thumbnails/        # Thumbnail images
├── analysis/              # (when --extract-ui enabled)
│   ├── *_analysis.json    # Complete analysis data
│   ├── *_tokens.css       # Extracted design tokens
│   ├── *_colors.css       # Color palette CSS
│   ├── *_typography.css   # Typography CSS
│   ├── *_accessibility.md # Accessibility report
│   ├── *_meta.html        # SEO meta tags
│   └── *_performance.txt  # Performance report
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
├── analyzer/               # UI analysis modules
│   ├── __init__.py
│   ├── screenshot.py       # Responsive screenshot capture
│   ├── styles.py           # CSS/style analysis
│   ├── components.py       # UI component detection
│   ├── colors.py           # Color palette extraction
│   ├── typography.py       # Typography analysis
│   ├── accessibility.py    # WCAG compliance checking
│   ├── seo.py              # SEO metadata extraction
│   ├── forms.py            # Form detection
│   ├── performance.py      # Performance analysis
│   └── ui_extractor.py     # Unified UI extraction
├── utils/
│   ├── __init__.py
│   ├── log.py              # Logging utilities
│   ├── paths.py            # URL/path helpers
│   └── robots.py           # robots.txt handling
└── web/
    ├── __init__.py
    ├── app.py              # Flask web application
    ├── run.py              # Web UI entry point
    ├── templates/          # HTML templates
    └── static/             # CSS and static files
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
- **flask**: Web UI framework

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
