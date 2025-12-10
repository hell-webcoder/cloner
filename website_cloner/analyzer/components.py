"""
Component detector module for identifying UI components.

Detects common UI patterns like navigation, forms, cards, buttons, etc.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from enum import Enum

from bs4 import BeautifulSoup, Tag

from ..utils.log import get_logger


class ComponentType(Enum):
    """Types of UI components."""
    NAVIGATION = "navigation"
    HEADER = "header"
    FOOTER = "footer"
    SIDEBAR = "sidebar"
    HERO = "hero"
    CARD = "card"
    BUTTON = "button"
    FORM = "form"
    INPUT = "input"
    MODAL = "modal"
    DROPDOWN = "dropdown"
    TABS = "tabs"
    ACCORDION = "accordion"
    CAROUSEL = "carousel"
    TABLE = "table"
    LIST = "list"
    GRID = "grid"
    IMAGE_GALLERY = "image_gallery"
    BREADCRUMB = "breadcrumb"
    PAGINATION = "pagination"
    ALERT = "alert"
    BADGE = "badge"
    PROGRESS = "progress"
    TOOLTIP = "tooltip"
    AVATAR = "avatar"
    MENU = "menu"
    SEARCH = "search"
    SOCIAL = "social"
    CTA = "call_to_action"
    TESTIMONIAL = "testimonial"
    PRICING = "pricing"
    FEATURE = "feature"
    UNKNOWN = "unknown"


@dataclass
class DetectedComponent:
    """Represents a detected UI component."""
    component_type: ComponentType
    selector: str
    tag_name: str
    class_names: List[str]
    id_attr: Optional[str]
    inner_html: str
    attributes: Dict[str, str]
    children_count: int
    text_content: str
    confidence: float  # 0.0 to 1.0


@dataclass
class ComponentAnalysisResult:
    """Result of component detection analysis."""
    components: List[DetectedComponent] = field(default_factory=list)
    component_counts: Dict[str, int] = field(default_factory=dict)
    structure_info: Dict[str, Any] = field(default_factory=dict)
    framework_detected: Optional[str] = None
    css_framework: Optional[str] = None


class ComponentDetector:
    """
    Detects and classifies UI components in web pages.
    
    Identifies common patterns like navigation, cards, forms,
    and recognizes popular frameworks.
    """
    
    # Class patterns for component detection
    COMPONENT_PATTERNS = {
        ComponentType.NAVIGATION: [
            r'\bnav\b', r'\bnavbar\b', r'\bnavigation\b', r'\bmenu\b',
            r'\btop-bar\b', r'\bheader-nav\b', r'\bmain-nav\b'
        ],
        ComponentType.HEADER: [
            r'\bheader\b', r'\bsite-header\b', r'\bpage-header\b',
            r'\bmasthead\b', r'\btop-header\b'
        ],
        ComponentType.FOOTER: [
            r'\bfooter\b', r'\bsite-footer\b', r'\bpage-footer\b',
            r'\bbottom\b'
        ],
        ComponentType.SIDEBAR: [
            r'\bsidebar\b', r'\bside-nav\b', r'\bside-menu\b',
            r'\baside\b', r'\bdrawer\b'
        ],
        ComponentType.HERO: [
            r'\bhero\b', r'\bjumbotron\b', r'\bbanner\b', r'\bsplash\b',
            r'\bintro\b', r'\blead\b'
        ],
        ComponentType.CARD: [
            r'\bcard\b', r'\bpanel\b', r'\btile\b', r'\bbox\b',
            r'\bitem\b', r'\bpost\b'
        ],
        ComponentType.BUTTON: [
            r'\bbtn\b', r'\bbutton\b', r'\bcta\b'
        ],
        ComponentType.FORM: [
            r'\bform\b', r'\bform-group\b', r'\binput-group\b'
        ],
        ComponentType.MODAL: [
            r'\bmodal\b', r'\bdialog\b', r'\bpopup\b', r'\boverlay\b',
            r'\blightbox\b'
        ],
        ComponentType.DROPDOWN: [
            r'\bdropdown\b', r'\bselect\b', r'\bpopover\b', r'\bmenu\b'
        ],
        ComponentType.TABS: [
            r'\btab\b', r'\btabs\b', r'\btab-content\b', r'\btab-pane\b'
        ],
        ComponentType.ACCORDION: [
            r'\baccordion\b', r'\bcollapse\b', r'\bexpandable\b',
            r'\bfaq\b'
        ],
        ComponentType.CAROUSEL: [
            r'\bcarousel\b', r'\bslider\b', r'\bslideshow\b',
            r'\bswiper\b', r'\bslick\b', r'\bowl\b'
        ],
        ComponentType.TABLE: [
            r'\btable\b', r'\bdata-table\b', r'\bgrid-table\b'
        ],
        ComponentType.LIST: [
            r'\blist\b', r'\blist-group\b', r'\bitems\b'
        ],
        ComponentType.GRID: [
            r'\bgrid\b', r'\brow\b', r'\bcol\b', r'\bcolumn\b',
            r'\blayout\b'
        ],
        ComponentType.IMAGE_GALLERY: [
            r'\bgallery\b', r'\bgrid-gallery\b', r'\bimage-grid\b',
            r'\bportfolio\b'
        ],
        ComponentType.BREADCRUMB: [
            r'\bbreadcrumb\b', r'\bcrumbs\b'
        ],
        ComponentType.PAGINATION: [
            r'\bpagination\b', r'\bpager\b', r'\bpage-nav\b'
        ],
        ComponentType.ALERT: [
            r'\balert\b', r'\bnotification\b', r'\bnotice\b',
            r'\bmessage\b', r'\btoast\b'
        ],
        ComponentType.BADGE: [
            r'\bbadge\b', r'\blabel\b', r'\btag\b', r'\bchip\b'
        ],
        ComponentType.PROGRESS: [
            r'\bprogress\b', r'\bloading\b', r'\bspinner\b'
        ],
        ComponentType.AVATAR: [
            r'\bavatar\b', r'\bprofile-pic\b', r'\buser-image\b'
        ],
        ComponentType.SEARCH: [
            r'\bsearch\b', r'\bsearch-form\b', r'\bsearchbox\b'
        ],
        ComponentType.SOCIAL: [
            r'\bsocial\b', r'\bshare\b', r'\bfollow\b'
        ],
        ComponentType.TESTIMONIAL: [
            r'\btestimonial\b', r'\bquote\b', r'\breview\b'
        ],
        ComponentType.PRICING: [
            r'\bpricing\b', r'\bprice\b', r'\bplan\b'
        ],
        ComponentType.FEATURE: [
            r'\bfeature\b', r'\bbenefits\b', r'\bservices\b'
        ],
    }
    
    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        'bootstrap': [r'\bbootstrap\b', r'\bbs-', r'\bbtn-primary\b'],
        'tailwind': [r'\btailwind\b', r'\btext-\w+-\d+\b', r'\bbg-\w+-\d+\b'],
        'material-ui': [r'\bMui', r'\bmaterial\b', r'\bmat-'],
        'bulma': [r'\bbulma\b', r'\bis-\w+\b'],
        'foundation': [r'\bfoundation\b', r'\brow\s+column\b'],
        'semantic-ui': [r'\bsemantic\b', r'\bui\s+\w+\b'],
        'chakra': [r'\bchakra\b', r'\bcss-\w+\b'],
        'ant-design': [r'\bant-', r'\bantd\b'],
    }
    
    # JS Framework detection
    JS_FRAMEWORK_PATTERNS = {
        'react': [r'\b__react', r'\breact-', r'\bdata-reactroot'],
        'vue': [r'\bv-', r'\b__vue', r'\bvue-'],
        'angular': [r'\bng-', r'\b_ng', r'\bangular'],
        'svelte': [r'\bsvelte-', r'\b__svelte'],
        'next': [r'\b__NEXT', r'\bnext-'],
        'nuxt': [r'\b__NUXT', r'\bnuxt-'],
        'gatsby': [r'\bgatsby-', r'\b___gatsby'],
    }
    
    def __init__(self):
        """Initialize the component detector."""
        self.logger = get_logger("components")
        
        # Compile patterns
        self._compiled_patterns = {
            comp_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for comp_type, patterns in self.COMPONENT_PATTERNS.items()
        }
        
        self._framework_patterns = {
            name: [re.compile(p, re.IGNORECASE) for p in patterns]
            for name, patterns in self.FRAMEWORK_PATTERNS.items()
        }
        
        self._js_framework_patterns = {
            name: [re.compile(p, re.IGNORECASE) for p in patterns]
            for name, patterns in self.JS_FRAMEWORK_PATTERNS.items()
        }
    
    def detect_components(self, html: str) -> ComponentAnalysisResult:
        """
        Detect UI components in HTML content.
        
        Args:
            html: HTML content to analyze
            
        Returns:
            ComponentAnalysisResult with detected components
        """
        result = ComponentAnalysisResult()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        
        # Detect frameworks first
        result.css_framework = self._detect_css_framework(html)
        result.framework_detected = self._detect_js_framework(html)
        
        # Analyze document structure
        result.structure_info = self._analyze_structure(soup)
        
        # Detect components by tag
        self._detect_by_tag(soup, result)
        
        # Detect components by class/attribute patterns
        self._detect_by_patterns(soup, result)
        
        # Count components by type
        for component in result.components:
            type_name = component.component_type.value
            result.component_counts[type_name] = \
                result.component_counts.get(type_name, 0) + 1
        
        return result
    
    def _detect_css_framework(self, html: str) -> Optional[str]:
        """Detect CSS framework used in the page."""
        for framework, patterns in self._framework_patterns.items():
            for pattern in patterns:
                if pattern.search(html):
                    return framework
        return None
    
    def _detect_js_framework(self, html: str) -> Optional[str]:
        """Detect JavaScript framework used in the page."""
        for framework, patterns in self._js_framework_patterns.items():
            for pattern in patterns:
                if pattern.search(html):
                    return framework
        return None
    
    def _analyze_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze the overall document structure."""
        structure = {
            'has_header': bool(soup.find('header')),
            'has_footer': bool(soup.find('footer')),
            'has_main': bool(soup.find('main')),
            'has_aside': bool(soup.find('aside')),
            'has_nav': bool(soup.find('nav')),
            'has_article': bool(soup.find('article')),
            'has_section': len(soup.find_all('section')),
            'heading_structure': self._get_heading_structure(soup),
            'semantic_score': 0,
            'total_elements': len(soup.find_all()),
        }
        
        # Calculate semantic score
        semantic_tags = ['header', 'footer', 'main', 'nav', 'article', 'section', 'aside']
        for tag in semantic_tags:
            if soup.find(tag):
                structure['semantic_score'] += 1
        
        structure['semantic_score'] = structure['semantic_score'] / len(semantic_tags)
        
        return structure
    
    def _get_heading_structure(self, soup: BeautifulSoup) -> Dict[str, int]:
        """Get the heading structure of the document."""
        headings = {}
        for i in range(1, 7):
            count = len(soup.find_all(f'h{i}'))
            if count > 0:
                headings[f'h{i}'] = count
        return headings
    
    def _detect_by_tag(
        self,
        soup: BeautifulSoup,
        result: ComponentAnalysisResult
    ) -> None:
        """Detect components by semantic HTML tags."""
        tag_mappings = {
            'nav': ComponentType.NAVIGATION,
            'header': ComponentType.HEADER,
            'footer': ComponentType.FOOTER,
            'aside': ComponentType.SIDEBAR,
            'form': ComponentType.FORM,
            'table': ComponentType.TABLE,
            'button': ComponentType.BUTTON,
        }
        
        for tag, comp_type in tag_mappings.items():
            for elem in soup.find_all(tag):
                component = self._create_component(elem, comp_type, 0.9)
                result.components.append(component)
    
    def _detect_by_patterns(
        self,
        soup: BeautifulSoup,
        result: ComponentAnalysisResult
    ) -> None:
        """Detect components by class/attribute patterns."""
        seen_selectors: Set[str] = set()
        
        for elem in soup.find_all(True):  # All elements
            if not isinstance(elem, Tag):
                continue
            
            classes = elem.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()
            
            class_str = ' '.join(classes)
            id_attr = elem.get('id', '')
            
            # Skip if already processed
            selector = self._build_selector(elem)
            if selector in seen_selectors:
                continue
            
            # Check against patterns
            detected_type = None
            confidence = 0.0
            
            for comp_type, patterns in self._compiled_patterns.items():
                for pattern in patterns:
                    if pattern.search(class_str) or (id_attr and pattern.search(id_attr)):
                        detected_type = comp_type
                        confidence = 0.8
                        break
                if detected_type:
                    break
            
            if detected_type:
                component = self._create_component(elem, detected_type, confidence)
                result.components.append(component)
                seen_selectors.add(selector)
    
    def _create_component(
        self,
        elem: Tag,
        comp_type: ComponentType,
        confidence: float
    ) -> DetectedComponent:
        """Create a DetectedComponent from a BeautifulSoup element."""
        classes = elem.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()
        
        # Get a clean version of inner HTML (limited length)
        inner_html = str(elem)
        if len(inner_html) > 1000:
            inner_html = inner_html[:1000] + "..."
        
        # Get text content (limited)
        text = elem.get_text(strip=True)
        if len(text) > 500:
            text = text[:500] + "..."
        
        # Build attributes dict
        attrs = dict(elem.attrs)
        if 'class' in attrs:
            attrs['class'] = ' '.join(attrs['class']) if isinstance(attrs['class'], list) else attrs['class']
        
        return DetectedComponent(
            component_type=comp_type,
            selector=self._build_selector(elem),
            tag_name=elem.name,
            class_names=classes,
            id_attr=elem.get('id'),
            inner_html=inner_html,
            attributes=attrs,
            children_count=len(list(elem.children)),
            text_content=text,
            confidence=confidence
        )
    
    def _build_selector(self, elem: Tag) -> str:
        """Build a CSS selector for an element."""
        tag = elem.name
        
        # Use ID if available
        if elem.get('id'):
            return f"{tag}#{elem['id']}"
        
        # Use classes
        classes = elem.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()
        
        if classes:
            class_selector = '.'.join(classes[:3])  # Limit to 3 classes
            return f"{tag}.{class_selector}"
        
        return tag
    
    def get_component_tree(self, html: str) -> Dict[str, Any]:
        """
        Build a hierarchical tree of detected components.
        
        Args:
            html: HTML content to analyze
            
        Returns:
            Nested dictionary representing component hierarchy
        """
        result = self.detect_components(html)
        
        tree = {
            'structure': result.structure_info,
            'framework': result.framework_detected,
            'css_framework': result.css_framework,
            'components': {},
        }
        
        # Group components by type
        for component in result.components:
            type_name = component.component_type.value
            if type_name not in tree['components']:
                tree['components'][type_name] = []
            
            tree['components'][type_name].append({
                'selector': component.selector,
                'tag': component.tag_name,
                'classes': component.class_names,
                'id': component.id_attr,
                'confidence': component.confidence,
            })
        
        return tree
    
    def extract_component_html(
        self,
        html: str,
        component_type: ComponentType
    ) -> List[str]:
        """
        Extract HTML for all components of a specific type.
        
        Args:
            html: HTML content to search
            component_type: Type of component to extract
            
        Returns:
            List of HTML strings for matching components
        """
        result = self.detect_components(html)
        
        return [
            comp.inner_html
            for comp in result.components
            if comp.component_type == component_type
        ]
