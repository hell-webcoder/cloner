"""
Analyzer module for comprehensive website UI extraction.

Contains components for analyzing screenshots, styles, components, 
colors, typography, accessibility, SEO, and more.
"""

from .screenshot import ScreenshotCapture, ScreenshotResult, VIEWPORT_PRESETS
from .styles import StyleAnalyzer, StyleAnalysisResult, DesignTokens
from .components import ComponentDetector, ComponentAnalysisResult, ComponentType
from .colors import ColorExtractor, ColorPalette, Color
from .typography import TypographyAnalyzer, TypographyAnalysisResult
from .accessibility import AccessibilityChecker, AccessibilityResult, AccessibilityIssue
from .seo import SEOExtractor, SEOAnalysisResult
from .forms import FormAnalyzer, FormAnalysisResult, FormInfo
from .performance import PerformanceAnalyzer, PerformanceResult
from .ui_extractor import UIExtractor, UIExtractionResult

__all__ = [
    # Main extractor
    "UIExtractor",
    "UIExtractionResult",
    # Screenshot
    "ScreenshotCapture",
    "ScreenshotResult",
    "VIEWPORT_PRESETS",
    # Styles
    "StyleAnalyzer",
    "StyleAnalysisResult",
    "DesignTokens",
    # Components
    "ComponentDetector",
    "ComponentAnalysisResult",
    "ComponentType",
    # Colors
    "ColorExtractor",
    "ColorPalette",
    "Color",
    # Typography
    "TypographyAnalyzer",
    "TypographyAnalysisResult",
    # Accessibility
    "AccessibilityChecker",
    "AccessibilityResult",
    "AccessibilityIssue",
    # SEO
    "SEOExtractor",
    "SEOAnalysisResult",
    # Forms
    "FormAnalyzer",
    "FormAnalysisResult",
    "FormInfo",
    # Performance
    "PerformanceAnalyzer",
    "PerformanceResult",
]
