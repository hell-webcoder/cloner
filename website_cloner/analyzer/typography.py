"""
Typography analyzer module for extracting font information.

Extracts font families, sizes, weights, and other typography details.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from collections import Counter

from bs4 import BeautifulSoup

from ..utils.log import get_logger


@dataclass
class FontInfo:
    """Information about a font used on the page."""
    family: str
    weight: Optional[str] = None
    style: Optional[str] = None
    size: Optional[str] = None
    line_height: Optional[str] = None
    source: Optional[str] = None  # 'google', 'local', 'system', 'custom'
    url: Optional[str] = None
    usage_count: int = 1


@dataclass
class TextStyle:
    """Represents a text style configuration."""
    name: str
    font_family: str
    font_size: str
    font_weight: str
    line_height: str
    letter_spacing: Optional[str] = None
    text_transform: Optional[str] = None
    selector: Optional[str] = None


@dataclass
class TypographyAnalysisResult:
    """Result of typography analysis."""
    fonts: List[FontInfo] = field(default_factory=list)
    font_families: List[str] = field(default_factory=list)
    font_sizes: Dict[str, int] = field(default_factory=dict)
    font_weights: Dict[str, int] = field(default_factory=dict)
    line_heights: Dict[str, int] = field(default_factory=dict)
    heading_styles: List[TextStyle] = field(default_factory=list)
    body_styles: List[TextStyle] = field(default_factory=list)
    google_fonts: List[str] = field(default_factory=list)
    font_face_declarations: List[Dict[str, str]] = field(default_factory=list)
    text_scale: Dict[str, str] = field(default_factory=dict)


class TypographyAnalyzer:
    """
    Analyzes typography in web pages.
    
    Extracts font information, text styles, and builds a typography scale.
    """
    
    # Common font stacks
    SYSTEM_FONTS = {
        'system-ui', '-apple-system', 'blinkmacsystemfont', 'segoe ui',
        'roboto', 'helvetica neue', 'arial', 'sans-serif', 'serif',
        'monospace', 'ui-sans-serif', 'ui-serif', 'ui-monospace'
    }
    
    # Google Fonts URL pattern
    GOOGLE_FONTS_PATTERN = re.compile(
        r'fonts\.googleapis\.com/css[^"\']+family=([^"\'&]+)',
        re.IGNORECASE
    )
    
    # Font property patterns
    FONT_SIZE_PATTERN = re.compile(
        r'font-size\s*:\s*([^;]+)',
        re.IGNORECASE
    )
    
    FONT_WEIGHT_PATTERN = re.compile(
        r'font-weight\s*:\s*([^;]+)',
        re.IGNORECASE
    )
    
    FONT_FAMILY_PATTERN = re.compile(
        r'font-family\s*:\s*([^;]+)',
        re.IGNORECASE
    )
    
    LINE_HEIGHT_PATTERN = re.compile(
        r'line-height\s*:\s*([^;]+)',
        re.IGNORECASE
    )
    
    FONT_FACE_PATTERN = re.compile(
        r'@font-face\s*{([^}]+)}',
        re.IGNORECASE | re.DOTALL
    )
    
    def __init__(self):
        """Initialize the typography analyzer."""
        self.logger = get_logger("typography")
    
    def analyze(self, html: str, css_content: str = "") -> TypographyAnalysisResult:
        """
        Analyze typography in HTML and CSS content.
        
        Args:
            html: HTML content to analyze
            css_content: Optional additional CSS content
            
        Returns:
            TypographyAnalysisResult with extracted typography information
        """
        result = TypographyAnalysisResult()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        
        # Extract Google Fonts
        result.google_fonts = self._extract_google_fonts(soup, html)
        
        # Extract @font-face declarations
        result.font_face_declarations = self._extract_font_faces(html, css_content)
        
        # Extract font families from styles
        all_css = self._collect_all_css(soup, css_content)
        result.font_families = self._extract_font_families(all_css)
        
        # Extract font sizes and weights
        result.font_sizes = self._extract_font_sizes(all_css)
        result.font_weights = self._extract_font_weights(all_css)
        result.line_heights = self._extract_line_heights(all_css)
        
        # Build font info list
        result.fonts = self._build_font_list(result)
        
        # Extract heading styles
        result.heading_styles = self._extract_heading_styles(soup, all_css)
        
        # Extract body styles
        result.body_styles = self._extract_body_styles(soup, all_css)
        
        # Build text scale
        result.text_scale = self._build_text_scale(result)
        
        return result
    
    def _extract_google_fonts(
        self,
        soup: BeautifulSoup,
        html: str
    ) -> List[str]:
        """Extract Google Fonts used in the page."""
        fonts = set()
        
        # Check link tags
        for link in soup.find_all('link', href=True):
            href = link.get('href', '')
            match = self.GOOGLE_FONTS_PATTERN.search(href)
            if match:
                font_string = match.group(1)
                # Parse font names
                for font in font_string.split('|'):
                    font_name = font.split(':')[0].replace('+', ' ')
                    fonts.add(font_name)
        
        # Check @import statements
        for match in self.GOOGLE_FONTS_PATTERN.finditer(html):
            font_string = match.group(1)
            for font in font_string.split('|'):
                font_name = font.split(':')[0].replace('+', ' ')
                fonts.add(font_name)
        
        return sorted(list(fonts))
    
    def _extract_font_faces(
        self,
        html: str,
        css_content: str
    ) -> List[Dict[str, str]]:
        """Extract @font-face declarations."""
        font_faces = []
        combined = html + '\n' + css_content
        
        for match in self.FONT_FACE_PATTERN.finditer(combined):
            content = match.group(1)
            font_face = {}
            
            # Parse properties
            for line in content.split(';'):
                if ':' in line:
                    prop, value = line.split(':', 1)
                    prop = prop.strip().lower()
                    value = value.strip()
                    if prop and value:
                        font_face[prop] = value
            
            if font_face:
                font_faces.append(font_face)
        
        return font_faces
    
    def _collect_all_css(
        self,
        soup: BeautifulSoup,
        css_content: str
    ) -> str:
        """Collect all CSS from the page."""
        css_parts = []
        
        # Inline styles
        for elem in soup.find_all(style=True):
            css_parts.append(elem.get('style', ''))
        
        # Style tags
        for style in soup.find_all('style'):
            if style.string:
                css_parts.append(style.string)
        
        # Additional CSS
        if css_content:
            css_parts.append(css_content)
        
        return '\n'.join(css_parts)
    
    def _extract_font_families(self, css: str) -> List[str]:
        """Extract unique font families from CSS."""
        families = Counter()
        
        for match in self.FONT_FAMILY_PATTERN.finditer(css):
            value = match.group(1).strip()
            # Parse font family list
            for font in value.split(','):
                font = font.strip().strip('"\'').lower()
                if font and font not in {'inherit', 'initial', 'unset'}:
                    families[font] += 1
        
        # Sort by usage count
        return [f for f, _ in families.most_common()]
    
    def _extract_font_sizes(self, css: str) -> Dict[str, int]:
        """Extract font sizes and their usage counts."""
        sizes = Counter()
        
        for match in self.FONT_SIZE_PATTERN.finditer(css):
            value = match.group(1).strip()
            if value and value not in {'inherit', 'initial', 'unset'}:
                sizes[value] += 1
        
        return dict(sizes.most_common())
    
    def _extract_font_weights(self, css: str) -> Dict[str, int]:
        """Extract font weights and their usage counts."""
        weights = Counter()
        
        for match in self.FONT_WEIGHT_PATTERN.finditer(css):
            value = match.group(1).strip()
            if value and value not in {'inherit', 'initial', 'unset'}:
                weights[value] += 1
        
        return dict(weights.most_common())
    
    def _extract_line_heights(self, css: str) -> Dict[str, int]:
        """Extract line heights and their usage counts."""
        line_heights = Counter()
        
        for match in self.LINE_HEIGHT_PATTERN.finditer(css):
            value = match.group(1).strip()
            if value and value not in {'inherit', 'initial', 'unset', 'normal'}:
                line_heights[value] += 1
        
        return dict(line_heights.most_common())
    
    def _build_font_list(
        self,
        result: TypographyAnalysisResult
    ) -> List[FontInfo]:
        """Build a list of FontInfo objects from extracted data."""
        fonts = []
        
        # Add Google Fonts
        for font in result.google_fonts:
            fonts.append(FontInfo(
                family=font,
                source='google',
                url=f"https://fonts.googleapis.com/css?family={font.replace(' ', '+')}"
            ))
        
        # Add @font-face fonts
        for ff in result.font_face_declarations:
            family = ff.get('font-family', '').strip('"\'')
            if family:
                fonts.append(FontInfo(
                    family=family,
                    weight=ff.get('font-weight'),
                    style=ff.get('font-style'),
                    source='custom',
                    url=ff.get('src', '').split('url(')[-1].split(')')[0].strip('"\'')
                ))
        
        # Add other font families
        google_font_names = {f.lower() for f in result.google_fonts}
        custom_font_names = {
            ff.get('font-family', '').strip('"\'').lower()
            for ff in result.font_face_declarations
        }
        
        for family in result.font_families:
            if family.lower() not in google_font_names and family.lower() not in custom_font_names:
                source = 'system' if family.lower() in self.SYSTEM_FONTS else 'local'
                fonts.append(FontInfo(
                    family=family,
                    source=source
                ))
        
        return fonts
    
    def _extract_heading_styles(
        self,
        soup: BeautifulSoup,
        css: str
    ) -> List[TextStyle]:
        """Extract styles for heading elements."""
        styles = []
        
        # Common heading selectors
        heading_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        
        for tag in heading_tags:
            elements = soup.find_all(tag)
            if elements:
                # Try to extract style from first element or CSS
                style = self._extract_text_style(
                    tag,
                    elements[0] if elements else None,
                    css
                )
                if style:
                    style.name = tag.upper()
                    styles.append(style)
        
        return styles
    
    def _extract_body_styles(
        self,
        soup: BeautifulSoup,
        css: str
    ) -> List[TextStyle]:
        """Extract styles for body text elements."""
        styles = []
        
        # Common body text selectors
        body_selectors = ['body', 'p', '.text', '.body-text', 'article', 'main']
        
        for selector in body_selectors:
            if selector.startswith('.'):
                elements = soup.select(selector)
            else:
                elements = soup.find_all(selector)
            
            if elements:
                style = self._extract_text_style(
                    selector,
                    elements[0] if elements else None,
                    css
                )
                if style:
                    style.name = selector
                    styles.append(style)
        
        return styles
    
    def _extract_text_style(
        self,
        selector: str,
        element: Optional[Any],
        css: str
    ) -> Optional[TextStyle]:
        """Extract text style for an element or selector."""
        style_str = ""
        
        # Get inline style
        if element and hasattr(element, 'get'):
            style_str = element.get('style', '')
        
        # Try to find in CSS (simplified)
        selector_pattern = re.compile(
            rf'{re.escape(selector)}\s*{{([^}}]+)}}',
            re.IGNORECASE
        )
        for match in selector_pattern.finditer(css):
            style_str += '; ' + match.group(1)
        
        if not style_str:
            return None
        
        # Parse style properties
        font_family = 'inherit'
        font_size = 'inherit'
        font_weight = 'inherit'
        line_height = 'inherit'
        letter_spacing = None
        text_transform = None
        
        for match in self.FONT_FAMILY_PATTERN.finditer(style_str):
            font_family = match.group(1).strip()
        
        for match in self.FONT_SIZE_PATTERN.finditer(style_str):
            font_size = match.group(1).strip()
        
        for match in self.FONT_WEIGHT_PATTERN.finditer(style_str):
            font_weight = match.group(1).strip()
        
        for match in self.LINE_HEIGHT_PATTERN.finditer(style_str):
            line_height = match.group(1).strip()
        
        letter_match = re.search(r'letter-spacing\s*:\s*([^;]+)', style_str, re.IGNORECASE)
        if letter_match:
            letter_spacing = letter_match.group(1).strip()
        
        transform_match = re.search(r'text-transform\s*:\s*([^;]+)', style_str, re.IGNORECASE)
        if transform_match:
            text_transform = transform_match.group(1).strip()
        
        return TextStyle(
            name='',
            font_family=font_family,
            font_size=font_size,
            font_weight=font_weight,
            line_height=line_height,
            letter_spacing=letter_spacing,
            text_transform=text_transform,
            selector=selector
        )
    
    def _build_text_scale(
        self,
        result: TypographyAnalysisResult
    ) -> Dict[str, str]:
        """Build a typography scale from extracted sizes."""
        scale = {}
        
        # Standard scale names
        scale_names = [
            'xs', 'sm', 'base', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl'
        ]
        
        # Sort sizes by pixel value
        def parse_size(size: str) -> float:
            try:
                if 'px' in size:
                    return float(size.replace('px', ''))
                elif 'rem' in size:
                    return float(size.replace('rem', '')) * 16
                elif 'em' in size:
                    return float(size.replace('em', '')) * 16
                elif '%' in size:
                    return float(size.replace('%', '')) * 0.16
                else:
                    return float(size)
            except (ValueError, TypeError):
                return 0
        
        sorted_sizes = sorted(
            result.font_sizes.keys(),
            key=parse_size
        )
        
        # Map to scale names
        if sorted_sizes:
            step = max(1, len(sorted_sizes) // len(scale_names))
            for i, name in enumerate(scale_names):
                idx = min(i * step, len(sorted_sizes) - 1)
                scale[name] = sorted_sizes[idx]
        
        return scale
    
    def generate_typography_css(
        self,
        result: TypographyAnalysisResult
    ) -> str:
        """
        Generate CSS for typography from analysis result.
        
        Args:
            result: TypographyAnalysisResult to convert
            
        Returns:
            CSS string with typography styles
        """
        lines = []
        
        # Font imports
        if result.google_fonts:
            fonts_param = '|'.join(f.replace(' ', '+') for f in result.google_fonts)
            lines.append(f"@import url('https://fonts.googleapis.com/css?family={fonts_param}&display=swap');")
            lines.append("")
        
        # Root variables
        lines.append(":root {")
        
        # Font families
        if result.font_families:
            lines.append("  /* Font Families */")
            lines.append(f"  --font-primary: {result.font_families[0]};")
            if len(result.font_families) > 1:
                lines.append(f"  --font-secondary: {result.font_families[1]};")
            lines.append("")
        
        # Font scale
        if result.text_scale:
            lines.append("  /* Typography Scale */")
            for name, size in result.text_scale.items():
                lines.append(f"  --text-{name}: {size};")
            lines.append("")
        
        # Font weights
        if result.font_weights:
            lines.append("  /* Font Weights */")
            weight_names = ['light', 'normal', 'medium', 'semibold', 'bold']
            weights = list(result.font_weights.keys())[:5]
            for i, weight in enumerate(weights):
                if i < len(weight_names):
                    lines.append(f"  --font-{weight_names[i]}: {weight};")
            lines.append("")
        
        # Line heights
        if result.line_heights:
            lines.append("  /* Line Heights */")
            heights = list(result.line_heights.keys())[:3]
            line_height_names = ['tight', 'normal', 'loose']
            for i, height in enumerate(heights):
                if i < len(line_height_names):
                    lines.append(f"  --leading-{line_height_names[i]}: {height};")
        
        lines.append("}")
        lines.append("")
        
        # Heading styles
        if result.heading_styles:
            lines.append("/* Heading Styles */")
            for style in result.heading_styles:
                lines.append(f"{style.selector or style.name.lower()} {{")
                lines.append(f"  font-family: {style.font_family};")
                lines.append(f"  font-size: {style.font_size};")
                lines.append(f"  font-weight: {style.font_weight};")
                lines.append(f"  line-height: {style.line_height};")
                if style.letter_spacing:
                    lines.append(f"  letter-spacing: {style.letter_spacing};")
                if style.text_transform:
                    lines.append(f"  text-transform: {style.text_transform};")
                lines.append("}")
                lines.append("")
        
        return '\n'.join(lines)
