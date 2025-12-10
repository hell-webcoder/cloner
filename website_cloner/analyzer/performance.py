"""
Performance analyzer module for capturing performance metrics.

Extracts performance-related information from web pages.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from bs4 import BeautifulSoup

from ..utils.log import get_logger


@dataclass
class ResourceInfo:
    """Information about a resource."""
    url: str
    resource_type: str  # script, stylesheet, image, font, etc.
    size: Optional[int] = None
    is_critical: bool = False
    is_render_blocking: bool = False
    has_async: bool = False
    has_defer: bool = False
    preload: bool = False


@dataclass
class PerformanceHints:
    """Performance optimization hints."""
    critical_css: List[str] = field(default_factory=list)
    lazy_load_candidates: List[str] = field(default_factory=list)
    unused_js_indicators: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)


@dataclass
class PerformanceResult:
    """Result of performance analysis."""
    # Resource counts
    total_scripts: int = 0
    total_stylesheets: int = 0
    total_images: int = 0
    total_fonts: int = 0
    
    # Resource lists
    scripts: List[ResourceInfo] = field(default_factory=list)
    stylesheets: List[ResourceInfo] = field(default_factory=list)
    images: List[ResourceInfo] = field(default_factory=list)
    fonts: List[ResourceInfo] = field(default_factory=list)
    preloaded: List[ResourceInfo] = field(default_factory=list)
    
    # Metrics
    render_blocking_resources: int = 0
    async_scripts: int = 0
    defer_scripts: int = 0
    lazy_loaded_images: int = 0
    inline_scripts_count: int = 0
    inline_styles_count: int = 0
    
    # Hints
    hints: PerformanceHints = field(default_factory=PerformanceHints)
    
    # Score
    score: float = 100.0


class PerformanceAnalyzer:
    """
    Analyzes performance aspects of web pages.
    
    Extracts resource information and provides optimization hints.
    """
    
    def __init__(self):
        """Initialize the performance analyzer."""
        self.logger = get_logger("performance")
    
    def analyze(self, html: str) -> PerformanceResult:
        """
        Analyze performance aspects of HTML content.
        
        Args:
            html: HTML content to analyze
            
        Returns:
            PerformanceResult with performance information
        """
        result = PerformanceResult()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        
        # Analyze different resource types
        self._analyze_scripts(soup, result)
        self._analyze_stylesheets(soup, result)
        self._analyze_images(soup, result)
        self._analyze_fonts(soup, result)
        self._analyze_preloads(soup, result)
        self._analyze_inline_resources(soup, result)
        
        # Generate optimization hints
        result.hints = self._generate_hints(result, soup)
        
        # Calculate performance score
        result.score = self._calculate_score(result)
        
        return result
    
    def _analyze_scripts(
        self,
        soup: BeautifulSoup,
        result: PerformanceResult
    ) -> None:
        """Analyze script elements."""
        scripts = soup.find_all('script')
        
        for script in scripts:
            src = script.get('src')
            
            if not src:
                # Inline script
                result.inline_scripts_count += 1
                continue
            
            is_async = script.has_attr('async')
            is_defer = script.has_attr('defer')
            is_module = script.get('type') == 'module'
            
            # Render blocking if not async, defer, or module
            is_render_blocking = not (is_async or is_defer or is_module)
            
            resource = ResourceInfo(
                url=src,
                resource_type='script',
                is_render_blocking=is_render_blocking,
                has_async=is_async,
                has_defer=is_defer
            )
            
            result.scripts.append(resource)
            
            if is_async:
                result.async_scripts += 1
            if is_defer:
                result.defer_scripts += 1
            if is_render_blocking:
                result.render_blocking_resources += 1
        
        result.total_scripts = len(result.scripts)
    
    def _analyze_stylesheets(
        self,
        soup: BeautifulSoup,
        result: PerformanceResult
    ) -> None:
        """Analyze stylesheet elements."""
        # Link stylesheets
        links = soup.find_all('link', rel=lambda x: x and 'stylesheet' in str(x))
        
        for link in links:
            href = link.get('href')
            if not href:
                continue
            
            # Check if it's preloaded or has media query
            media = link.get('media', '')
            is_print_only = media == 'print'
            
            resource = ResourceInfo(
                url=href,
                resource_type='stylesheet',
                is_render_blocking=not is_print_only,
                is_critical=not is_print_only
            )
            
            result.stylesheets.append(resource)
            
            if not is_print_only:
                result.render_blocking_resources += 1
        
        result.total_stylesheets = len(result.stylesheets)
    
    def _analyze_images(
        self,
        soup: BeautifulSoup,
        result: PerformanceResult
    ) -> None:
        """Analyze image elements."""
        images = soup.find_all('img')
        
        for img in images:
            src = img.get('src', '') or img.get('data-src', '')
            if not src or src.startswith('data:'):
                continue
            
            # Check for lazy loading
            loading = img.get('loading', '')
            has_lazy_class = 'lazy' in ' '.join(img.get('class', []))
            is_lazy = loading == 'lazy' or img.has_attr('data-src') or has_lazy_class
            
            resource = ResourceInfo(
                url=src,
                resource_type='image',
                is_critical=False
            )
            
            result.images.append(resource)
            
            if is_lazy:
                result.lazy_loaded_images += 1
        
        result.total_images = len(result.images)
    
    def _analyze_fonts(
        self,
        soup: BeautifulSoup,
        result: PerformanceResult
    ) -> None:
        """Analyze font resources."""
        # Preload fonts
        preload_fonts = soup.find_all('link', rel='preload', attrs={'as': 'font'})
        
        for link in preload_fonts:
            href = link.get('href')
            if href:
                result.fonts.append(ResourceInfo(
                    url=href,
                    resource_type='font',
                    preload=True
                ))
        
        # Font URLs in CSS (heuristic)
        for style in soup.find_all('style'):
            if style.string:
                font_pattern = re.compile(r'url\(["\']?([^"\')\s]+\.(woff2?|ttf|otf|eot))["\']?\)')
                for match in font_pattern.finditer(style.string):
                    result.fonts.append(ResourceInfo(
                        url=match.group(1),
                        resource_type='font',
                        preload=False
                    ))
        
        result.total_fonts = len(result.fonts)
    
    def _analyze_preloads(
        self,
        soup: BeautifulSoup,
        result: PerformanceResult
    ) -> None:
        """Analyze preloaded resources."""
        preloads = soup.find_all('link', rel='preload')
        
        for link in preloads:
            href = link.get('href')
            as_type = link.get('as', 'unknown')
            
            if href:
                result.preloaded.append(ResourceInfo(
                    url=href,
                    resource_type=as_type,
                    preload=True
                ))
    
    def _analyze_inline_resources(
        self,
        soup: BeautifulSoup,
        result: PerformanceResult
    ) -> None:
        """Analyze inline styles and scripts."""
        # Count inline styles (already counted scripts above)
        style_tags = soup.find_all('style')
        result.inline_styles_count = len(style_tags)
        
        # Count inline style attributes
        elements_with_style = soup.find_all(style=True)
        result.inline_styles_count += len(elements_with_style)
    
    def _generate_hints(
        self,
        result: PerformanceResult,
        soup: BeautifulSoup
    ) -> PerformanceHints:
        """Generate performance optimization hints."""
        hints = PerformanceHints()
        
        # Render blocking suggestions
        if result.render_blocking_resources > 3:
            hints.optimization_suggestions.append(
                f"Consider reducing render-blocking resources ({result.render_blocking_resources} found)"
            )
        
        # Script optimization suggestions
        non_async_scripts = result.total_scripts - result.async_scripts - result.defer_scripts
        if non_async_scripts > 0:
            hints.optimization_suggestions.append(
                f"Add async or defer to {non_async_scripts} script(s) to improve loading"
            )
        
        # Image lazy loading suggestions
        non_lazy_images = result.total_images - result.lazy_loaded_images
        if non_lazy_images > 5:
            hints.optimization_suggestions.append(
                f"Consider lazy loading {non_lazy_images} below-the-fold images"
            )
            # Add candidates
            for img in result.images[5:]:  # Skip first 5 as likely above-fold
                hints.lazy_load_candidates.append(img.url)
        
        # Font preloading
        non_preloaded_fonts = sum(1 for f in result.fonts if not f.preload)
        if non_preloaded_fonts > 0 and result.total_fonts > 0:
            hints.optimization_suggestions.append(
                f"Preload {non_preloaded_fonts} font file(s) for faster text rendering"
            )
        
        # Inline CSS suggestions
        if result.inline_styles_count > 10:
            hints.optimization_suggestions.append(
                "Consider extracting inline styles to external CSS files"
            )
        
        # Inline scripts suggestions
        if result.inline_scripts_count > 5:
            hints.optimization_suggestions.append(
                "Consider moving inline scripts to external files for caching"
            )
        
        # Critical CSS hints
        for css in result.stylesheets[:3]:  # First 3 stylesheets likely critical
            hints.critical_css.append(css.url)
        
        return hints
    
    def _calculate_score(self, result: PerformanceResult) -> float:
        """Calculate performance score based on analysis."""
        score = 100.0
        
        # Penalize render-blocking resources
        score -= result.render_blocking_resources * 3
        
        # Reward async/defer usage
        if result.total_scripts > 0:
            async_ratio = (result.async_scripts + result.defer_scripts) / result.total_scripts
            score += async_ratio * 10
        
        # Reward lazy loading
        if result.total_images > 5:
            lazy_ratio = result.lazy_loaded_images / result.total_images
            score += lazy_ratio * 10
        
        # Penalize too many inline resources
        if result.inline_scripts_count > 10:
            score -= 5
        if result.inline_styles_count > 20:
            score -= 5
        
        # Penalize too many total resources
        total_resources = (
            result.total_scripts +
            result.total_stylesheets +
            result.total_images +
            result.total_fonts
        )
        if total_resources > 50:
            score -= (total_resources - 50) * 0.5
        
        return max(0, min(100, round(score, 1)))
    
    def generate_performance_report(self, result: PerformanceResult) -> str:
        """
        Generate a text performance report.
        
        Args:
            result: PerformanceResult to report
            
        Returns:
            Formatted text report
        """
        lines = [
            "=" * 60,
            "PERFORMANCE ANALYSIS REPORT",
            "=" * 60,
            "",
            f"Performance Score: {result.score}/100",
            "",
            "RESOURCE SUMMARY",
            "-" * 40,
            f"  Scripts: {result.total_scripts}",
            f"    - Async: {result.async_scripts}",
            f"    - Defer: {result.defer_scripts}",
            f"    - Inline: {result.inline_scripts_count}",
            f"  Stylesheets: {result.total_stylesheets}",
            f"  Images: {result.total_images}",
            f"    - Lazy loaded: {result.lazy_loaded_images}",
            f"  Fonts: {result.total_fonts}",
            f"  Preloaded resources: {len(result.preloaded)}",
            "",
            f"Render-blocking resources: {result.render_blocking_resources}",
            "",
        ]
        
        if result.hints.optimization_suggestions:
            lines.extend([
                "OPTIMIZATION SUGGESTIONS",
                "-" * 40,
            ])
            for i, suggestion in enumerate(result.hints.optimization_suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
            lines.append("")
        
        if result.hints.critical_css:
            lines.extend([
                "CRITICAL CSS FILES",
                "-" * 40,
            ])
            for css in result.hints.critical_css:
                lines.append(f"  - {css}")
            lines.append("")
        
        lines.append("=" * 60)
        
        return '\n'.join(lines)
