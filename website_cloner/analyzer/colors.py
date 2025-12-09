"""
Color extractor module for extracting color palettes from websites.

Extracts colors from CSS, styles, and images to build a comprehensive color palette.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from collections import Counter

from bs4 import BeautifulSoup

from ..utils.log import get_logger


@dataclass
class Color:
    """Represents a color with various formats."""
    original: str
    hex: str
    rgb: Tuple[int, int, int]
    hsl: Tuple[int, int, int]
    name: Optional[str] = None
    usage_count: int = 1
    contexts: List[str] = field(default_factory=list)


@dataclass
class ColorPalette:
    """Collection of colors extracted from a website."""
    primary_colors: List[Color] = field(default_factory=list)
    secondary_colors: List[Color] = field(default_factory=list)
    background_colors: List[Color] = field(default_factory=list)
    text_colors: List[Color] = field(default_factory=list)
    accent_colors: List[Color] = field(default_factory=list)
    all_colors: List[Color] = field(default_factory=list)
    color_count: int = 0
    dominant_color: Optional[Color] = None


class ColorExtractor:
    """
    Extracts and analyzes colors from web pages.
    
    Parses CSS and HTML to extract color values and build
    a comprehensive color palette.
    """
    
    # Color extraction patterns
    HEX_PATTERN = re.compile(r'#([0-9a-fA-F]{3,8})\b')
    RGB_PATTERN = re.compile(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*[\d.]+)?\s*\)')
    HSL_PATTERN = re.compile(r'hsla?\s*\(\s*(\d+)\s*,\s*(\d+)%\s*,\s*(\d+)%(?:\s*,\s*[\d.]+)?\s*\)')
    
    # Named colors (subset of CSS named colors)
    NAMED_COLORS = {
        'black': '#000000', 'white': '#ffffff', 'red': '#ff0000',
        'green': '#008000', 'blue': '#0000ff', 'yellow': '#ffff00',
        'cyan': '#00ffff', 'magenta': '#ff00ff', 'gray': '#808080',
        'grey': '#808080', 'silver': '#c0c0c0', 'maroon': '#800000',
        'olive': '#808000', 'lime': '#00ff00', 'aqua': '#00ffff',
        'teal': '#008080', 'navy': '#000080', 'fuchsia': '#ff00ff',
        'purple': '#800080', 'orange': '#ffa500', 'pink': '#ffc0cb',
        'brown': '#a52a2a', 'gold': '#ffd700', 'coral': '#ff7f50',
        'crimson': '#dc143c', 'darkblue': '#00008b', 'darkgreen': '#006400',
        'darkred': '#8b0000', 'lightblue': '#add8e6', 'lightgreen': '#90ee90',
        'lightgray': '#d3d3d3', 'lightgrey': '#d3d3d3', 'darkgray': '#a9a9a9',
        'darkgrey': '#a9a9a9', 'transparent': None, 'inherit': None,
        'currentcolor': None, 'initial': None, 'unset': None,
    }
    
    # Color property names for context detection
    BACKGROUND_PROPS = {'background', 'background-color', 'bg'}
    TEXT_PROPS = {'color', 'text-color'}
    BORDER_PROPS = {'border', 'border-color', 'outline', 'outline-color'}
    
    def __init__(self):
        """Initialize the color extractor."""
        self.logger = get_logger("colors")
    
    def extract_colors(self, html: str, css_content: str = "") -> ColorPalette:
        """
        Extract colors from HTML and CSS content.
        
        Args:
            html: HTML content to analyze
            css_content: Optional additional CSS content
            
        Returns:
            ColorPalette with extracted colors
        """
        palette = ColorPalette()
        color_contexts: Dict[str, List[str]] = {}  # hex -> contexts
        
        # Parse HTML
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        
        # Extract from inline styles
        for elem in soup.find_all(style=True):
            style = elem.get('style', '')
            self._extract_from_style(style, color_contexts)
        
        # Extract from style tags
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                self._extract_from_css(style_tag.string, color_contexts)
        
        # Extract from additional CSS
        if css_content:
            self._extract_from_css(css_content, color_contexts)
        
        # Build color objects
        all_colors = []
        for hex_color, contexts in color_contexts.items():
            if hex_color and hex_color != 'transparent':
                color = self._create_color(hex_color, contexts)
                if color:
                    all_colors.append(color)
        
        # Sort by usage count
        all_colors.sort(key=lambda c: c.usage_count, reverse=True)
        palette.all_colors = all_colors
        palette.color_count = len(all_colors)
        
        if all_colors:
            palette.dominant_color = all_colors[0]
        
        # Categorize colors
        self._categorize_colors(palette)
        
        return palette
    
    def _extract_from_style(
        self,
        style: str,
        color_contexts: Dict[str, List[str]]
    ) -> None:
        """Extract colors from an inline style string."""
        # Parse style properties
        for prop in style.split(';'):
            if ':' in prop:
                name, value = prop.split(':', 1)
                name = name.strip().lower()
                value = value.strip()
                
                # Determine context
                context = 'other'
                if any(p in name for p in self.BACKGROUND_PROPS):
                    context = 'background'
                elif any(p in name for p in self.TEXT_PROPS):
                    context = 'text'
                elif any(p in name for p in self.BORDER_PROPS):
                    context = 'border'
                
                # Extract colors from value
                colors = self._extract_colors_from_value(value)
                for hex_color in colors:
                    if hex_color not in color_contexts:
                        color_contexts[hex_color] = []
                    color_contexts[hex_color].append(context)
    
    def _extract_from_css(
        self,
        css: str,
        color_contexts: Dict[str, List[str]]
    ) -> None:
        """Extract colors from CSS content."""
        # Extract from CSS variable definitions
        var_pattern = re.compile(r'--[\w-]+\s*:\s*([^;]+)')
        for match in var_pattern.finditer(css):
            value = match.group(1)
            colors = self._extract_colors_from_value(value)
            for hex_color in colors:
                if hex_color not in color_contexts:
                    color_contexts[hex_color] = []
                color_contexts[hex_color].append('variable')
        
        # Extract from property values
        prop_pattern = re.compile(r'([\w-]+)\s*:\s*([^;{}]+)')
        for match in prop_pattern.finditer(css):
            name = match.group(1).strip().lower()
            value = match.group(2).strip()
            
            # Determine context
            context = 'other'
            if any(p in name for p in self.BACKGROUND_PROPS):
                context = 'background'
            elif any(p in name for p in self.TEXT_PROPS):
                context = 'text'
            elif any(p in name for p in self.BORDER_PROPS):
                context = 'border'
            
            colors = self._extract_colors_from_value(value)
            for hex_color in colors:
                if hex_color not in color_contexts:
                    color_contexts[hex_color] = []
                color_contexts[hex_color].append(context)
    
    def _extract_colors_from_value(self, value: str) -> List[str]:
        """Extract all color values from a CSS value string."""
        colors = []
        
        # Check hex colors
        for match in self.HEX_PATTERN.finditer(value):
            hex_val = match.group(1)
            normalized = self._normalize_hex(hex_val)
            if normalized:
                colors.append(normalized)
        
        # Check rgb/rgba colors
        for match in self.RGB_PATTERN.finditer(value):
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            hex_color = self._rgb_to_hex(r, g, b)
            colors.append(hex_color)
        
        # Check hsl/hsla colors
        for match in self.HSL_PATTERN.finditer(value):
            h, s, l = int(match.group(1)), int(match.group(2)), int(match.group(3))
            rgb = self._hsl_to_rgb(h, s, l)
            hex_color = self._rgb_to_hex(*rgb)
            colors.append(hex_color)
        
        # Check named colors
        value_lower = value.lower()
        for name, hex_val in self.NAMED_COLORS.items():
            if re.search(r'\b' + name + r'\b', value_lower) and hex_val:
                colors.append(hex_val)
        
        return colors
    
    def _normalize_hex(self, hex_val: str) -> Optional[str]:
        """Normalize hex color to 6-digit format."""
        hex_val = hex_val.lower()
        
        if len(hex_val) == 3:
            # Expand 3-digit hex
            hex_val = ''.join(c * 2 for c in hex_val)
        elif len(hex_val) == 8:
            # Strip alpha channel
            hex_val = hex_val[:6]
        elif len(hex_val) != 6:
            return None
        
        try:
            # Validate hex
            int(hex_val, 16)
            return f"#{hex_val}"
        except ValueError:
            return None
    
    def _rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """Convert RGB to hex color."""
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB."""
        hex_val = hex_color.lstrip('#')
        return tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
    
    def _hsl_to_rgb(self, h: int, s: int, l: int) -> Tuple[int, int, int]:
        """Convert HSL to RGB."""
        h = h / 360
        s = s / 100
        l = l / 100
        
        if s == 0:
            r = g = b = l
        else:
            def hue_to_rgb(p, q, t):
                if t < 0:
                    t += 1
                if t > 1:
                    t -= 1
                if t < 1/6:
                    return p + (q - p) * 6 * t
                if t < 1/2:
                    return q
                if t < 2/3:
                    return p + (q - p) * (2/3 - t) * 6
                return p
            
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue_to_rgb(p, q, h + 1/3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1/3)
        
        return (int(r * 255), int(g * 255), int(b * 255))
    
    def _rgb_to_hsl(self, r: int, g: int, b: int) -> Tuple[int, int, int]:
        """Convert RGB to HSL."""
        r, g, b = r / 255, g / 255, b / 255
        
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        l = (max_c + min_c) / 2
        
        if max_c == min_c:
            h = s = 0
        else:
            d = max_c - min_c
            s = d / (2 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)
            
            if max_c == r:
                h = (g - b) / d + (6 if g < b else 0)
            elif max_c == g:
                h = (b - r) / d + 2
            else:
                h = (r - g) / d + 4
            
            h /= 6
        
        return (int(h * 360), int(s * 100), int(l * 100))
    
    def _create_color(self, hex_color: str, contexts: List[str]) -> Optional[Color]:
        """Create a Color object from hex value and contexts."""
        try:
            rgb = self._hex_to_rgb(hex_color)
            hsl = self._rgb_to_hsl(*rgb)
            
            return Color(
                original=hex_color,
                hex=hex_color,
                rgb=rgb,
                hsl=hsl,
                usage_count=len(contexts),
                contexts=list(set(contexts))
            )
        except Exception:
            return None
    
    def _categorize_colors(self, palette: ColorPalette) -> None:
        """Categorize colors into primary, secondary, etc."""
        background_colors = []
        text_colors = []
        accent_colors = []
        
        for color in palette.all_colors:
            if 'background' in color.contexts:
                background_colors.append(color)
            if 'text' in color.contexts:
                text_colors.append(color)
            if 'border' in color.contexts or 'variable' in color.contexts:
                accent_colors.append(color)
        
        palette.background_colors = background_colors[:10]
        palette.text_colors = text_colors[:10]
        palette.accent_colors = accent_colors[:10]
        
        # Primary colors are most used
        palette.primary_colors = palette.all_colors[:5]
        
        # Secondary colors are next most used that aren't primary
        seen = set(c.hex for c in palette.primary_colors)
        palette.secondary_colors = [
            c for c in palette.all_colors[5:15]
            if c.hex not in seen
        ][:5]
    
    def get_contrast_ratio(self, color1: str, color2: str) -> float:
        """
        Calculate the contrast ratio between two colors.
        
        Args:
            color1: First color in hex format
            color2: Second color in hex format
            
        Returns:
            Contrast ratio (1.0 to 21.0)
        """
        def get_luminance(hex_color: str) -> float:
            rgb = self._hex_to_rgb(hex_color)
            rgb_normalized = [c / 255 for c in rgb]
            rgb_linear = [
                c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
                for c in rgb_normalized
            ]
            return 0.2126 * rgb_linear[0] + 0.7152 * rgb_linear[1] + 0.0722 * rgb_linear[2]
        
        l1 = get_luminance(color1)
        l2 = get_luminance(color2)
        
        lighter = max(l1, l2)
        darker = min(l1, l2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    def check_wcag_compliance(
        self,
        foreground: str,
        background: str
    ) -> Dict[str, bool]:
        """
        Check WCAG color contrast compliance.
        
        Args:
            foreground: Foreground color in hex
            background: Background color in hex
            
        Returns:
            Dictionary with compliance results for different levels
        """
        ratio = self.get_contrast_ratio(foreground, background)
        
        return {
            'ratio': ratio,
            'aa_normal': ratio >= 4.5,
            'aa_large': ratio >= 3.0,
            'aaa_normal': ratio >= 7.0,
            'aaa_large': ratio >= 4.5,
        }
    
    def generate_palette_css(self, palette: ColorPalette) -> str:
        """
        Generate CSS custom properties from the color palette.
        
        Args:
            palette: ColorPalette to convert
            
        Returns:
            CSS string with color custom properties
        """
        lines = [":root {"]
        
        # Primary colors
        lines.append("  /* Primary Colors */")
        for i, color in enumerate(palette.primary_colors):
            lines.append(f"  --color-primary-{i + 1}: {color.hex};")
        
        # Secondary colors
        if palette.secondary_colors:
            lines.append("")
            lines.append("  /* Secondary Colors */")
            for i, color in enumerate(palette.secondary_colors):
                lines.append(f"  --color-secondary-{i + 1}: {color.hex};")
        
        # Background colors
        if palette.background_colors:
            lines.append("")
            lines.append("  /* Background Colors */")
            for i, color in enumerate(palette.background_colors[:5]):
                lines.append(f"  --color-bg-{i + 1}: {color.hex};")
        
        # Text colors
        if palette.text_colors:
            lines.append("")
            lines.append("  /* Text Colors */")
            for i, color in enumerate(palette.text_colors[:5]):
                lines.append(f"  --color-text-{i + 1}: {color.hex};")
        
        lines.append("}")
        
        return '\n'.join(lines)
