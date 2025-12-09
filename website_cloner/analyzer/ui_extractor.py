"""
Comprehensive UI extractor that combines all analyzers.

Provides a unified interface for extracting all UI information from websites.
"""

import os
import json
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from playwright.async_api import Page

from .screenshot import ScreenshotCapture, ScreenshotResult
from .styles import StyleAnalyzer, StyleAnalysisResult
from .components import ComponentDetector, ComponentAnalysisResult
from .colors import ColorExtractor, ColorPalette
from .typography import TypographyAnalyzer, TypographyAnalysisResult
from .accessibility import AccessibilityChecker, AccessibilityResult
from .seo import SEOExtractor, SEOAnalysisResult
from .forms import FormAnalyzer, FormAnalysisResult
from .performance import PerformanceAnalyzer, PerformanceResult

from ..utils.log import get_logger
from ..utils.paths import ensure_dir


@dataclass
class UIExtractionResult:
    """Complete result of UI extraction for a page."""
    url: str
    screenshots: Optional[ScreenshotResult] = None
    styles: Optional[StyleAnalysisResult] = None
    components: Optional[ComponentAnalysisResult] = None
    colors: Optional[ColorPalette] = None
    typography: Optional[TypographyAnalysisResult] = None
    accessibility: Optional[AccessibilityResult] = None
    seo: Optional[SEOAnalysisResult] = None
    forms: Optional[FormAnalysisResult] = None
    performance: Optional[PerformanceResult] = None
    errors: List[str] = field(default_factory=list)


class UIExtractor:
    """
    Comprehensive UI extractor combining all analyzers.
    
    Extracts screenshots, styles, components, colors, typography,
    accessibility information, SEO metadata, forms, and performance metrics.
    """
    
    def __init__(
        self,
        output_dir: str,
        capture_screenshots: bool = True,
        analyze_styles: bool = True,
        detect_components: bool = True,
        extract_colors: bool = True,
        analyze_typography: bool = True,
        check_accessibility: bool = True,
        extract_seo: bool = True,
        analyze_forms: bool = True,
        analyze_performance: bool = True,
        viewports: Optional[List[str]] = None
    ):
        """
        Initialize the UI extractor.
        
        Args:
            output_dir: Directory to save extracted information
            capture_screenshots: Whether to capture screenshots
            analyze_styles: Whether to analyze CSS styles
            detect_components: Whether to detect UI components
            extract_colors: Whether to extract color palettes
            analyze_typography: Whether to analyze typography
            check_accessibility: Whether to check accessibility
            extract_seo: Whether to extract SEO metadata
            analyze_forms: Whether to analyze forms
            analyze_performance: Whether to analyze performance
            viewports: List of viewport names for screenshots
        """
        self.output_dir = output_dir
        self.analysis_dir = os.path.join(output_dir, "analysis")
        self.logger = get_logger("ui_extractor")
        
        # Flags
        self._capture_screenshots = capture_screenshots
        self._analyze_styles = analyze_styles
        self._detect_components = detect_components
        self._extract_colors = extract_colors
        self._analyze_typography = analyze_typography
        self._check_accessibility = check_accessibility
        self._extract_seo = extract_seo
        self._analyze_forms = analyze_forms
        self._analyze_performance = analyze_performance
        
        # Initialize analyzers
        if capture_screenshots:
            self.screenshot_capture = ScreenshotCapture(output_dir, viewports)
        if analyze_styles:
            self.style_analyzer = StyleAnalyzer()
        if detect_components:
            self.component_detector = ComponentDetector()
        if extract_colors:
            self.color_extractor = ColorExtractor()
        if analyze_typography:
            self.typography_analyzer = TypographyAnalyzer()
        if check_accessibility:
            self.accessibility_checker = AccessibilityChecker()
        if extract_seo:
            self.seo_extractor = SEOExtractor()
        if analyze_forms:
            self.form_analyzer = FormAnalyzer()
        if analyze_performance:
            self.performance_analyzer = PerformanceAnalyzer()
        
        # Ensure directories exist
        ensure_dir(self.analysis_dir)
    
    async def extract(
        self,
        page: Page,
        url: str,
        html: str,
        css_content: str = ""
    ) -> UIExtractionResult:
        """
        Extract all UI information from a page.
        
        Args:
            page: Playwright page object (for screenshots)
            url: URL of the page
            html: HTML content of the page
            css_content: Optional additional CSS content
            
        Returns:
            UIExtractionResult with all extracted information
        """
        result = UIExtractionResult(url=url)
        
        # Capture screenshots
        if self._capture_screenshots and page:
            try:
                filename_base = self._url_to_filename(url)
                result.screenshots = await self.screenshot_capture.capture_page(
                    page, url, filename_base
                )
            except Exception as e:
                self.logger.error(f"Screenshot capture failed: {e}")
                result.errors.append(f"Screenshots: {str(e)}")
        
        # Analyze styles
        if self._analyze_styles:
            try:
                result.styles = self.style_analyzer.analyze_html(html, url)
            except Exception as e:
                self.logger.error(f"Style analysis failed: {e}")
                result.errors.append(f"Styles: {str(e)}")
        
        # Detect components
        if self._detect_components:
            try:
                result.components = self.component_detector.detect_components(html)
            except Exception as e:
                self.logger.error(f"Component detection failed: {e}")
                result.errors.append(f"Components: {str(e)}")
        
        # Extract colors
        if self._extract_colors:
            try:
                result.colors = self.color_extractor.extract_colors(html, css_content)
            except Exception as e:
                self.logger.error(f"Color extraction failed: {e}")
                result.errors.append(f"Colors: {str(e)}")
        
        # Analyze typography
        if self._analyze_typography:
            try:
                result.typography = self.typography_analyzer.analyze(html, css_content)
            except Exception as e:
                self.logger.error(f"Typography analysis failed: {e}")
                result.errors.append(f"Typography: {str(e)}")
        
        # Check accessibility
        if self._check_accessibility:
            try:
                result.accessibility = self.accessibility_checker.check(html)
            except Exception as e:
                self.logger.error(f"Accessibility check failed: {e}")
                result.errors.append(f"Accessibility: {str(e)}")
        
        # Extract SEO
        if self._extract_seo:
            try:
                result.seo = self.seo_extractor.extract(html, url)
            except Exception as e:
                self.logger.error(f"SEO extraction failed: {e}")
                result.errors.append(f"SEO: {str(e)}")
        
        # Analyze forms
        if self._analyze_forms:
            try:
                result.forms = self.form_analyzer.analyze(html)
            except Exception as e:
                self.logger.error(f"Form analysis failed: {e}")
                result.errors.append(f"Forms: {str(e)}")
        
        # Analyze performance
        if self._analyze_performance:
            try:
                result.performance = self.performance_analyzer.analyze(html)
            except Exception as e:
                self.logger.error(f"Performance analysis failed: {e}")
                result.errors.append(f"Performance: {str(e)}")
        
        return result
    
    def save_analysis(
        self,
        result: UIExtractionResult,
        filename_base: str
    ) -> Dict[str, str]:
        """
        Save analysis results to files.
        
        Args:
            result: UIExtractionResult to save
            filename_base: Base filename for saved files
            
        Returns:
            Dictionary mapping analysis type to file path
        """
        saved_files = {}
        
        # Save complete analysis as JSON
        analysis_data = self._result_to_dict(result)
        json_path = os.path.join(self.analysis_dir, f"{filename_base}_analysis.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)
        saved_files['analysis_json'] = json_path
        
        # Save design tokens CSS
        if result.styles and result.styles.design_tokens:
            tokens_css = self.style_analyzer.generate_css_from_tokens(
                result.styles.design_tokens
            )
            css_path = os.path.join(self.analysis_dir, f"{filename_base}_tokens.css")
            with open(css_path, 'w', encoding='utf-8') as f:
                f.write(tokens_css)
            saved_files['tokens_css'] = css_path
        
        # Save color palette CSS
        if result.colors:
            palette_css = self.color_extractor.generate_palette_css(result.colors)
            palette_path = os.path.join(self.analysis_dir, f"{filename_base}_colors.css")
            with open(palette_path, 'w', encoding='utf-8') as f:
                f.write(palette_css)
            saved_files['colors_css'] = palette_path
        
        # Save typography CSS
        if result.typography:
            typo_css = self.typography_analyzer.generate_typography_css(result.typography)
            typo_path = os.path.join(self.analysis_dir, f"{filename_base}_typography.css")
            with open(typo_path, 'w', encoding='utf-8') as f:
                f.write(typo_css)
            saved_files['typography_css'] = typo_path
        
        # Save accessibility report
        if result.accessibility:
            a11y_report = self._generate_accessibility_report(result.accessibility)
            a11y_path = os.path.join(self.analysis_dir, f"{filename_base}_accessibility.md")
            with open(a11y_path, 'w', encoding='utf-8') as f:
                f.write(a11y_report)
            saved_files['accessibility_report'] = a11y_path
        
        # Save SEO metadata
        if result.seo:
            meta_html = self.seo_extractor.generate_meta_tags(result.seo)
            meta_path = os.path.join(self.analysis_dir, f"{filename_base}_meta.html")
            with open(meta_path, 'w', encoding='utf-8') as f:
                f.write(meta_html)
            saved_files['meta_html'] = meta_path
        
        # Save performance report
        if result.performance:
            perf_report = self.performance_analyzer.generate_performance_report(
                result.performance
            )
            perf_path = os.path.join(self.analysis_dir, f"{filename_base}_performance.txt")
            with open(perf_path, 'w', encoding='utf-8') as f:
                f.write(perf_report)
            saved_files['performance_report'] = perf_path
        
        return saved_files
    
    def _url_to_filename(self, url: str) -> str:
        """Convert URL to a safe filename."""
        import re
        # Remove protocol
        filename = re.sub(r'^https?://', '', url)
        # Remove www
        filename = re.sub(r'^www\.', '', filename)
        # Replace unsafe characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        return filename[:80]
    
    def _result_to_dict(self, result: UIExtractionResult) -> Dict[str, Any]:
        """Convert UIExtractionResult to a dictionary."""
        data = {
            'url': result.url,
            'errors': result.errors,
        }
        
        if result.styles:
            data['styles'] = {
                'css_variables_count': len(result.styles.css_variables),
                'media_queries': result.styles.media_queries,
                'animations_count': len(result.styles.animations),
                'font_faces_count': len(result.styles.font_faces),
                'stylesheets': result.styles.stylesheets,
            }
        
        if result.components:
            data['components'] = {
                'counts': result.components.component_counts,
                'framework': result.components.framework_detected,
                'css_framework': result.components.css_framework,
                'structure': result.components.structure_info,
            }
        
        if result.colors:
            data['colors'] = {
                'count': result.colors.color_count,
                'dominant': result.colors.dominant_color.hex if result.colors.dominant_color else None,
                'primary': [c.hex for c in result.colors.primary_colors],
                'secondary': [c.hex for c in result.colors.secondary_colors],
                'background': [c.hex for c in result.colors.background_colors],
                'text': [c.hex for c in result.colors.text_colors],
            }
        
        if result.typography:
            data['typography'] = {
                'fonts': [f.family for f in result.typography.fonts],
                'google_fonts': result.typography.google_fonts,
                'font_sizes': result.typography.font_sizes,
                'text_scale': result.typography.text_scale,
            }
        
        if result.accessibility:
            data['accessibility'] = {
                'score': result.accessibility.score,
                'wcag_level': result.accessibility.wcag_level,
                'errors': result.accessibility.errors_count,
                'warnings': result.accessibility.warnings_count,
                'passed': result.accessibility.passed_checks,
                'issues': [
                    {
                        'rule': i.rule_id,
                        'description': i.description,
                        'level': i.level.value,
                        'wcag': i.wcag_criteria,
                    }
                    for i in result.accessibility.issues[:20]  # Limit to 20
                ],
            }
        
        if result.seo:
            data['seo'] = {
                'score': result.seo.score,
                'title': result.seo.title,
                'description': result.seo.meta_description,
                'canonical': result.seo.canonical_url,
                'headings': result.seo.headings,
                'open_graph': {
                    'title': result.seo.open_graph.title if result.seo.open_graph else None,
                    'image': result.seo.open_graph.image if result.seo.open_graph else None,
                },
                'structured_data_types': [
                    sd.type for sd in result.seo.structured_data
                ],
                'issues': result.seo.issues,
            }
        
        if result.forms:
            data['forms'] = {
                'total': result.forms.total_forms,
                'types': result.forms.form_types,
                'field_types': result.forms.field_types,
            }
        
        if result.performance:
            data['performance'] = {
                'score': result.performance.score,
                'scripts': result.performance.total_scripts,
                'stylesheets': result.performance.total_stylesheets,
                'images': result.performance.total_images,
                'render_blocking': result.performance.render_blocking_resources,
                'suggestions': result.performance.hints.optimization_suggestions,
            }
        
        if result.screenshots:
            data['screenshots'] = {
                'viewports': list(result.screenshots.screenshots.keys()) if hasattr(result.screenshots, 'screenshots') and result.screenshots.screenshots else [],
                'full_page': result.screenshots.full_page_path is not None if hasattr(result.screenshots, 'full_page_path') else False,
                'errors': result.screenshots.errors if hasattr(result.screenshots, 'errors') else [],
            }
        
        return data
    
    def _generate_accessibility_report(
        self,
        result: AccessibilityResult
    ) -> str:
        """Generate a markdown accessibility report."""
        lines = [
            "# Accessibility Report",
            "",
            f"**Score:** {result.score}/100",
            f"**WCAG Level:** {result.wcag_level}",
            "",
            "## Summary",
            f"- **Errors:** {result.errors_count}",
            f"- **Warnings:** {result.warnings_count}",
            f"- **Passed checks:** {len(result.passed_checks)}",
            "",
        ]
        
        if result.passed_checks:
            lines.extend([
                "## Passed Checks",
                "",
            ])
            for check in result.passed_checks:
                lines.append(f"- ✅ {check}")
            lines.append("")
        
        if result.issues:
            lines.extend([
                "## Issues",
                "",
            ])
            
            # Group by level
            errors = [i for i in result.issues if i.level.value == 'error']
            warnings = [i for i in result.issues if i.level.value == 'warning']
            info = [i for i in result.issues if i.level.value == 'info']
            
            if errors:
                lines.append("### Errors")
                lines.append("")
                for issue in errors:
                    lines.append(f"- ❌ **{issue.rule_id}** (WCAG {issue.wcag_criteria})")
                    lines.append(f"  - {issue.description}")
                    if issue.recommendation:
                        lines.append(f"  - 💡 {issue.recommendation}")
                lines.append("")
            
            if warnings:
                lines.append("### Warnings")
                lines.append("")
                for issue in warnings:
                    lines.append(f"- ⚠️ **{issue.rule_id}** (WCAG {issue.wcag_criteria})")
                    lines.append(f"  - {issue.description}")
                    if issue.recommendation:
                        lines.append(f"  - 💡 {issue.recommendation}")
                lines.append("")
            
            if info:
                lines.append("### Info")
                lines.append("")
                for issue in info:
                    lines.append(f"- ℹ️ **{issue.rule_id}** (WCAG {issue.wcag_criteria})")
                    lines.append(f"  - {issue.description}")
                lines.append("")
        
        return '\n'.join(lines)
