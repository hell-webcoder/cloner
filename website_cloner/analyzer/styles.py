"""
Style analyzer module for extracting CSS styles and design tokens.

Extracts computed styles, CSS custom properties, and design patterns.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..utils.log import get_logger


@dataclass
class CSSVariable:
    """Represents a CSS custom property."""
    name: str
    value: str
    category: str = "other"  # color, spacing, typography, etc.


@dataclass
class StyleRule:
    """Represents a CSS style rule."""
    selector: str
    properties: Dict[str, str]
    media_query: Optional[str] = None
    source_file: Optional[str] = None


@dataclass
class DesignTokens:
    """Collection of design tokens extracted from styles."""
    colors: Dict[str, str] = field(default_factory=dict)
    spacing: Dict[str, str] = field(default_factory=dict)
    typography: Dict[str, str] = field(default_factory=dict)
    shadows: Dict[str, str] = field(default_factory=dict)
    borders: Dict[str, str] = field(default_factory=dict)
    transitions: Dict[str, str] = field(default_factory=dict)
    breakpoints: Dict[str, str] = field(default_factory=dict)
    z_indexes: Dict[str, str] = field(default_factory=dict)


@dataclass
class StyleAnalysisResult:
    """Complete result of style analysis."""
    css_variables: List[CSSVariable] = field(default_factory=list)
    design_tokens: DesignTokens = field(default_factory=DesignTokens)
    media_queries: List[str] = field(default_factory=list)
    animations: List[Dict[str, Any]] = field(default_factory=list)
    font_faces: List[Dict[str, str]] = field(default_factory=list)
    style_rules_count: int = 0
    stylesheets: List[str] = field(default_factory=list)
    inline_styles_count: int = 0


class StyleAnalyzer:
    """
    Analyzes CSS styles and extracts design tokens.
    
    Parses stylesheets and inline styles to extract colors, spacing,
    typography, and other design patterns.
    """
    
    # Patterns for extracting values
    COLOR_PATTERN = re.compile(
        r'(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\)|'
        r'(?:aliceblue|antiquewhite|aqua|aquamarine|azure|beige|bisque|black|'
        r'blanchedalmond|blue|blueviolet|brown|burlywood|cadetblue|chartreuse|'
        r'chocolate|coral|cornflowerblue|cornsilk|crimson|cyan|darkblue|darkcyan|'
        r'darkgoldenrod|darkgray|darkgreen|darkgrey|darkkhaki|darkmagenta|darkolivegreen|'
        r'darkorange|darkorchid|darkred|darksalmon|darkseagreen|darkslateblue|'
        r'darkslategray|darkslategrey|darkturquoise|darkviolet|deeppink|deepskyblue|'
        r'dimgray|dimgrey|dodgerblue|firebrick|floralwhite|forestgreen|fuchsia|'
        r'gainsboro|ghostwhite|gold|goldenrod|gray|green|greenyellow|grey|honeydew|'
        r'hotpink|indianred|indigo|ivory|khaki|lavender|lavenderblush|lawngreen|'
        r'lemonchiffon|lightblue|lightcoral|lightcyan|lightgoldenrodyellow|lightgray|'
        r'lightgreen|lightgrey|lightpink|lightsalmon|lightseagreen|lightskyblue|'
        r'lightslategray|lightslategrey|lightsteelblue|lightyellow|lime|limegreen|'
        r'linen|magenta|maroon|mediumaquamarine|mediumblue|mediumorchid|mediumpurple|'
        r'mediumseagreen|mediumslateblue|mediumspringgreen|mediumturquoise|mediumvioletred|'
        r'midnightblue|mintcream|mistyrose|moccasin|navajowhite|navy|oldlace|olive|'
        r'olivedrab|orange|orangered|orchid|palegoldenrod|palegreen|paleturquoise|'
        r'palevioletred|papayawhip|peachpuff|peru|pink|plum|powderblue|purple|'
        r'rebeccapurple|red|rosybrown|royalblue|saddlebrown|salmon|sandybrown|seagreen|'
        r'seashell|sienna|silver|skyblue|slateblue|slategray|slategrey|snow|springgreen|'
        r'steelblue|tan|teal|thistle|tomato|turquoise|violet|wheat|white|whitesmoke|'
        r'yellow|yellowgreen))',
        re.IGNORECASE
    )
    
    SPACING_PATTERN = re.compile(r'(\d+(?:\.\d+)?(?:px|em|rem|%|vh|vw))')
    
    MEDIA_QUERY_PATTERN = re.compile(r'@media\s*([^{]+)', re.IGNORECASE)
    
    CSS_VAR_PATTERN = re.compile(r'--([a-zA-Z0-9_-]+)\s*:\s*([^;]+)')
    
    ANIMATION_PATTERN = re.compile(
        r'@keyframes\s+([a-zA-Z0-9_-]+)\s*{([^}]*(?:{[^}]*}[^}]*)*)}',
        re.IGNORECASE
    )
    
    FONT_FACE_PATTERN = re.compile(
        r'@font-face\s*{([^}]+)}',
        re.IGNORECASE
    )
    
    def __init__(self):
        """Initialize the style analyzer."""
        self.logger = get_logger("styles")
    
    def analyze_html(self, html: str, page_url: str) -> StyleAnalysisResult:
        """
        Analyze styles in HTML content.
        
        Args:
            html: HTML content to analyze
            page_url: URL of the page
            
        Returns:
            StyleAnalysisResult with extracted style information
        """
        result = StyleAnalysisResult()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        
        # Extract stylesheet links
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if href:
                full_url = urljoin(page_url, href)
                result.stylesheets.append(full_url)
        
        # Analyze inline styles
        inline_styles = []
        for elem in soup.find_all(style=True):
            inline_styles.append(elem.get('style', ''))
            result.inline_styles_count += 1
        
        # Analyze style tags
        style_content = []
        for style in soup.find_all('style'):
            if style.string:
                style_content.append(style.string)
        
        # Combine all CSS for analysis
        all_css = '\n'.join(style_content) + '\n' + '\n'.join(inline_styles)
        
        # Extract CSS variables
        result.css_variables = self._extract_css_variables(all_css)
        
        # Extract media queries
        result.media_queries = self._extract_media_queries(all_css)
        
        # Extract animations
        result.animations = self._extract_animations(all_css)
        
        # Extract font faces
        result.font_faces = self._extract_font_faces(all_css)
        
        # Build design tokens from variables
        result.design_tokens = self._build_design_tokens(result.css_variables, all_css)
        
        return result
    
    def analyze_css(self, css_content: str, css_url: str) -> StyleAnalysisResult:
        """
        Analyze a CSS file.
        
        Args:
            css_content: CSS file content
            css_url: URL of the CSS file
            
        Returns:
            StyleAnalysisResult with extracted style information
        """
        result = StyleAnalysisResult()
        result.stylesheets = [css_url]
        
        # Extract CSS variables
        result.css_variables = self._extract_css_variables(css_content)
        
        # Extract media queries
        result.media_queries = self._extract_media_queries(css_content)
        
        # Extract animations
        result.animations = self._extract_animations(css_content)
        
        # Extract font faces
        result.font_faces = self._extract_font_faces(css_content)
        
        # Build design tokens
        result.design_tokens = self._build_design_tokens(
            result.css_variables, css_content
        )
        
        return result
    
    def _extract_css_variables(self, css: str) -> List[CSSVariable]:
        """Extract CSS custom properties from CSS content."""
        variables = []
        
        for match in self.CSS_VAR_PATTERN.finditer(css):
            name = f"--{match.group(1)}"
            value = match.group(2).strip()
            
            # Categorize the variable
            category = self._categorize_variable(name, value)
            
            variables.append(CSSVariable(
                name=name,
                value=value,
                category=category
            ))
        
        return variables
    
    def _categorize_variable(self, name: str, value: str) -> str:
        """Categorize a CSS variable by its name and value."""
        name_lower = name.lower()
        
        # Check name patterns
        if any(k in name_lower for k in ['color', 'bg', 'background', 'text', 'border-color']):
            return 'color'
        if any(k in name_lower for k in ['spacing', 'margin', 'padding', 'gap', 'space']):
            return 'spacing'
        if any(k in name_lower for k in ['font', 'text', 'line-height', 'letter']):
            return 'typography'
        if any(k in name_lower for k in ['shadow', 'elevation']):
            return 'shadow'
        if any(k in name_lower for k in ['radius', 'rounded']):
            return 'border'
        if any(k in name_lower for k in ['transition', 'duration', 'timing']):
            return 'transition'
        if any(k in name_lower for k in ['z-index', 'layer']):
            return 'z-index'
        if any(k in name_lower for k in ['breakpoint', 'screen', 'media']):
            return 'breakpoint'
        
        # Check value patterns
        if self.COLOR_PATTERN.match(value):
            return 'color'
        if self.SPACING_PATTERN.match(value):
            return 'spacing'
        
        return 'other'
    
    def _extract_media_queries(self, css: str) -> List[str]:
        """Extract media queries from CSS content."""
        media_queries = set()
        
        for match in self.MEDIA_QUERY_PATTERN.finditer(css):
            query = match.group(1).strip()
            if query:
                media_queries.add(query)
        
        return sorted(list(media_queries))
    
    def _extract_animations(self, css: str) -> List[Dict[str, Any]]:
        """Extract keyframe animations from CSS content."""
        animations = []
        
        for match in self.ANIMATION_PATTERN.finditer(css):
            name = match.group(1)
            keyframes = match.group(2)
            
            animations.append({
                'name': name,
                'keyframes': keyframes.strip()
            })
        
        return animations
    
    def _extract_font_faces(self, css: str) -> List[Dict[str, str]]:
        """Extract @font-face declarations from CSS content."""
        font_faces = []
        
        for match in self.FONT_FACE_PATTERN.finditer(css):
            content = match.group(1)
            font_face = {}
            
            # Parse properties
            for line in content.split(';'):
                if ':' in line:
                    prop, value = line.split(':', 1)
                    prop = prop.strip()
                    value = value.strip()
                    if prop and value:
                        font_face[prop] = value
            
            if font_face:
                font_faces.append(font_face)
        
        return font_faces
    
    def _build_design_tokens(
        self,
        variables: List[CSSVariable],
        css: str
    ) -> DesignTokens:
        """Build design tokens from CSS variables and content."""
        tokens = DesignTokens()
        
        # Group variables by category
        for var in variables:
            if var.category == 'color':
                tokens.colors[var.name] = var.value
            elif var.category == 'spacing':
                tokens.spacing[var.name] = var.value
            elif var.category == 'typography':
                tokens.typography[var.name] = var.value
            elif var.category == 'shadow':
                tokens.shadows[var.name] = var.value
            elif var.category == 'border':
                tokens.borders[var.name] = var.value
            elif var.category == 'transition':
                tokens.transitions[var.name] = var.value
            elif var.category == 'breakpoint':
                tokens.breakpoints[var.name] = var.value
            elif var.category == 'z-index':
                tokens.z_indexes[var.name] = var.value
        
        # Extract breakpoints from media queries
        breakpoint_pattern = re.compile(r'(\d+(?:\.\d+)?)(px|em|rem)')
        for query in self._extract_media_queries(css):
            match = breakpoint_pattern.search(query)
            if match:
                value = f"{match.group(1)}{match.group(2)}"
                tokens.breakpoints[f"--breakpoint-{value}"] = value
        
        return tokens
    
    def extract_computed_styles(
        self,
        element_styles: Dict[str, Dict[str, str]]
    ) -> Dict[str, Dict[str, str]]:
        """
        Process computed styles from browser.
        
        Args:
            element_styles: Dictionary of element selectors to computed styles
            
        Returns:
            Processed styles grouped by category
        """
        categorized = {
            'layout': {},
            'typography': {},
            'colors': {},
            'spacing': {},
            'borders': {},
            'effects': {},
        }
        
        layout_props = {'display', 'position', 'flex', 'grid', 'float', 'clear'}
        typography_props = {'font', 'text', 'line-height', 'letter-spacing', 'word'}
        color_props = {'color', 'background', 'border-color', 'outline-color'}
        spacing_props = {'margin', 'padding', 'gap'}
        border_props = {'border', 'border-radius', 'outline'}
        effect_props = {'box-shadow', 'text-shadow', 'opacity', 'transform', 'transition'}
        
        for selector, styles in element_styles.items():
            for prop, value in styles.items():
                prop_lower = prop.lower()
                
                if any(p in prop_lower for p in layout_props):
                    categorized['layout'][f"{selector}:{prop}"] = value
                elif any(p in prop_lower for p in typography_props):
                    categorized['typography'][f"{selector}:{prop}"] = value
                elif any(p in prop_lower for p in color_props):
                    categorized['colors'][f"{selector}:{prop}"] = value
                elif any(p in prop_lower for p in spacing_props):
                    categorized['spacing'][f"{selector}:{prop}"] = value
                elif any(p in prop_lower for p in border_props):
                    categorized['borders'][f"{selector}:{prop}"] = value
                elif any(p in prop_lower for p in effect_props):
                    categorized['effects'][f"{selector}:{prop}"] = value
        
        return categorized
    
    def generate_css_from_tokens(self, tokens: DesignTokens) -> str:
        """
        Generate a CSS file from design tokens.
        
        Args:
            tokens: Design tokens to convert
            
        Returns:
            CSS string with custom properties
        """
        lines = [":root {"]
        
        # Colors
        if tokens.colors:
            lines.append("  /* Colors */")
            for name, value in sorted(tokens.colors.items()):
                lines.append(f"  {name}: {value};")
            lines.append("")
        
        # Spacing
        if tokens.spacing:
            lines.append("  /* Spacing */")
            for name, value in sorted(tokens.spacing.items()):
                lines.append(f"  {name}: {value};")
            lines.append("")
        
        # Typography
        if tokens.typography:
            lines.append("  /* Typography */")
            for name, value in sorted(tokens.typography.items()):
                lines.append(f"  {name}: {value};")
            lines.append("")
        
        # Shadows
        if tokens.shadows:
            lines.append("  /* Shadows */")
            for name, value in sorted(tokens.shadows.items()):
                lines.append(f"  {name}: {value};")
            lines.append("")
        
        # Borders
        if tokens.borders:
            lines.append("  /* Borders */")
            for name, value in sorted(tokens.borders.items()):
                lines.append(f"  {name}: {value};")
            lines.append("")
        
        # Transitions
        if tokens.transitions:
            lines.append("  /* Transitions */")
            for name, value in sorted(tokens.transitions.items()):
                lines.append(f"  {name}: {value};")
            lines.append("")
        
        # Breakpoints
        if tokens.breakpoints:
            lines.append("  /* Breakpoints */")
            for name, value in sorted(tokens.breakpoints.items()):
                lines.append(f"  {name}: {value};")
            lines.append("")
        
        # Z-indexes
        if tokens.z_indexes:
            lines.append("  /* Z-indexes */")
            for name, value in sorted(tokens.z_indexes.items()):
                lines.append(f"  {name}: {value};")
        
        lines.append("}")
        
        return '\n'.join(lines)
