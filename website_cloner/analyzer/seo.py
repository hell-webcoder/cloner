"""
SEO extractor module for extracting SEO-related metadata.

Extracts meta tags, structured data, Open Graph, and other SEO information.
"""

import re
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from bs4 import BeautifulSoup

from ..utils.log import get_logger


@dataclass
class MetaTag:
    """Represents a meta tag."""
    name: str
    content: str
    property_attr: Optional[str] = None


@dataclass
class OpenGraphData:
    """Open Graph metadata."""
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    image: Optional[str] = None
    type: Optional[str] = None
    site_name: Optional[str] = None
    locale: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)


@dataclass
class TwitterCardData:
    """Twitter Card metadata."""
    card_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    site: Optional[str] = None
    creator: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)


@dataclass
class StructuredData:
    """Schema.org structured data."""
    type: str
    data: Dict[str, Any]
    raw_json: str


@dataclass
class SEOAnalysisResult:
    """Result of SEO analysis."""
    title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical_url: Optional[str] = None
    meta_tags: List[MetaTag] = field(default_factory=list)
    open_graph: Optional[OpenGraphData] = None
    twitter_card: Optional[TwitterCardData] = None
    structured_data: List[StructuredData] = field(default_factory=list)
    headings: Dict[str, List[str]] = field(default_factory=dict)
    links: Dict[str, int] = field(default_factory=dict)
    images_count: int = 0
    images_without_alt: int = 0
    word_count: int = 0
    robots: Optional[str] = None
    hreflang: List[Dict[str, str]] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    score: float = 0.0


class SEOExtractor:
    """
    Extracts SEO information from web pages.
    
    Parses HTML to extract meta tags, structured data, and other
    SEO-relevant information.
    """
    
    def __init__(self):
        """Initialize the SEO extractor."""
        self.logger = get_logger("seo")
    
    def extract(self, html: str, page_url: str = "") -> SEOAnalysisResult:
        """
        Extract SEO information from HTML content.
        
        Args:
            html: HTML content to analyze
            page_url: URL of the page
            
        Returns:
            SEOAnalysisResult with extracted SEO information
        """
        result = SEOAnalysisResult()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        
        # Extract basic meta information
        result.title = self._extract_title(soup)
        result.meta_description = self._extract_meta_description(soup)
        result.canonical_url = self._extract_canonical(soup)
        result.robots = self._extract_robots(soup)
        
        # Extract all meta tags
        result.meta_tags = self._extract_meta_tags(soup)
        
        # Extract Open Graph data
        result.open_graph = self._extract_open_graph(soup)
        
        # Extract Twitter Card data
        result.twitter_card = self._extract_twitter_card(soup)
        
        # Extract structured data
        result.structured_data = self._extract_structured_data(soup)
        
        # Extract headings
        result.headings = self._extract_headings(soup)
        
        # Extract link information
        result.links = self._extract_links(soup, page_url)
        
        # Extract image information
        result.images_count, result.images_without_alt = self._extract_image_info(soup)
        
        # Calculate word count
        result.word_count = self._calculate_word_count(soup)
        
        # Extract hreflang
        result.hreflang = self._extract_hreflang(soup)
        
        # Analyze and find issues
        result.issues = self._analyze_issues(result)
        
        # Calculate SEO score
        result.score = self._calculate_score(result)
        
        return result
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title."""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        return None
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract meta description."""
        meta = soup.find('meta', attrs={'name': re.compile(r'^description$', re.I)})
        if meta:
            return meta.get('content', '')
        return None
    
    def _extract_canonical(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract canonical URL."""
        link = soup.find('link', attrs={'rel': 'canonical'})
        if link:
            return link.get('href', '')
        return None
    
    def _extract_robots(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract robots meta tag."""
        meta = soup.find('meta', attrs={'name': re.compile(r'^robots$', re.I)})
        if meta:
            return meta.get('content', '')
        return None
    
    def _extract_meta_tags(self, soup: BeautifulSoup) -> List[MetaTag]:
        """Extract all meta tags."""
        meta_tags = []
        
        for meta in soup.find_all('meta'):
            name = meta.get('name', '') or meta.get('property', '') or meta.get('http-equiv', '')
            content = meta.get('content', '')
            prop = meta.get('property', '')
            
            if name or prop:
                meta_tags.append(MetaTag(
                    name=name,
                    content=content,
                    property_attr=prop if prop else None
                ))
        
        return meta_tags
    
    def _extract_open_graph(self, soup: BeautifulSoup) -> OpenGraphData:
        """Extract Open Graph metadata."""
        og = OpenGraphData()
        
        og_tags = soup.find_all('meta', property=re.compile(r'^og:', re.I))
        
        for tag in og_tags:
            prop = tag.get('property', '').lower()
            content = tag.get('content', '')
            
            if prop == 'og:title':
                og.title = content
            elif prop == 'og:description':
                og.description = content
            elif prop == 'og:url':
                og.url = content
            elif prop == 'og:image':
                og.image = content
            elif prop == 'og:type':
                og.type = content
            elif prop == 'og:site_name':
                og.site_name = content
            elif prop == 'og:locale':
                og.locale = content
            else:
                og.extra[prop] = content
        
        return og
    
    def _extract_twitter_card(self, soup: BeautifulSoup) -> TwitterCardData:
        """Extract Twitter Card metadata."""
        tc = TwitterCardData()
        
        tc_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:', re.I)})
        
        for tag in tc_tags:
            name = tag.get('name', '').lower()
            content = tag.get('content', '')
            
            if name == 'twitter:card':
                tc.card_type = content
            elif name == 'twitter:title':
                tc.title = content
            elif name == 'twitter:description':
                tc.description = content
            elif name == 'twitter:image':
                tc.image = content
            elif name == 'twitter:site':
                tc.site = content
            elif name == 'twitter:creator':
                tc.creator = content
            else:
                tc.extra[name] = content
        
        return tc
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> List[StructuredData]:
        """Extract JSON-LD structured data."""
        structured = []
        
        for script in soup.find_all('script', type='application/ld+json'):
            if script.string:
                try:
                    data = json.loads(script.string)
                    
                    # Handle array of objects
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                structured.append(StructuredData(
                                    type=item.get('@type', 'Unknown'),
                                    data=item,
                                    raw_json=json.dumps(item)
                                ))
                    elif isinstance(data, dict):
                        structured.append(StructuredData(
                            type=data.get('@type', 'Unknown'),
                            data=data,
                            raw_json=script.string
                        ))
                except json.JSONDecodeError:
                    self.logger.debug("Failed to parse JSON-LD")
        
        return structured
    
    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract heading structure."""
        headings = {}
        
        for i in range(1, 7):
            tag = f'h{i}'
            found = soup.find_all(tag)
            if found:
                headings[tag] = [h.get_text(strip=True) for h in found]
        
        return headings
    
    def _extract_links(
        self,
        soup: BeautifulSoup,
        page_url: str
    ) -> Dict[str, int]:
        """Extract link statistics."""
        from urllib.parse import urlparse
        
        links = soup.find_all('a', href=True)
        internal = 0
        external = 0
        nofollow = 0
        
        page_domain = urlparse(page_url).netloc.lower() if page_url else ''
        
        for link in links:
            href = link.get('href', '')
            rel = link.get('rel', [])
            if isinstance(rel, str):
                rel = rel.split()
            
            if 'nofollow' in rel:
                nofollow += 1
            
            if href.startswith('#') or href.startswith('javascript:'):
                continue
            
            if href.startswith('http'):
                link_domain = urlparse(href).netloc.lower()
                if link_domain == page_domain:
                    internal += 1
                else:
                    external += 1
            else:
                internal += 1
        
        return {
            'total': len(links),
            'internal': internal,
            'external': external,
            'nofollow': nofollow
        }
    
    def _extract_image_info(self, soup: BeautifulSoup) -> tuple:
        """Extract image information."""
        images = soup.find_all('img')
        total = len(images)
        without_alt = sum(1 for img in images if not img.get('alt'))
        
        return total, without_alt
    
    def _calculate_word_count(self, soup: BeautifulSoup) -> int:
        """Calculate word count of main content."""
        # Remove script and style elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        words = text.split()
        
        return len(words)
    
    def _extract_hreflang(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract hreflang tags for internationalization."""
        hreflang_tags = []
        
        for link in soup.find_all('link', rel='alternate', hreflang=True):
            hreflang_tags.append({
                'lang': link.get('hreflang', ''),
                'url': link.get('href', '')
            })
        
        return hreflang_tags
    
    def _analyze_issues(self, result: SEOAnalysisResult) -> List[str]:
        """Analyze SEO issues."""
        issues = []
        
        # Title issues
        if not result.title:
            issues.append("Missing page title")
        elif len(result.title) < 30:
            issues.append("Title too short (< 30 characters)")
        elif len(result.title) > 60:
            issues.append("Title too long (> 60 characters)")
        
        # Meta description issues
        if not result.meta_description:
            issues.append("Missing meta description")
        elif len(result.meta_description) < 70:
            issues.append("Meta description too short (< 70 characters)")
        elif len(result.meta_description) > 160:
            issues.append("Meta description too long (> 160 characters)")
        
        # Canonical issues
        if not result.canonical_url:
            issues.append("Missing canonical URL")
        
        # Heading issues
        if 'h1' not in result.headings:
            issues.append("Missing H1 heading")
        elif len(result.headings.get('h1', [])) > 1:
            issues.append("Multiple H1 headings")
        
        # Image issues
        if result.images_without_alt > 0:
            issues.append(f"{result.images_without_alt} images missing alt text")
        
        # Open Graph issues
        if not result.open_graph.title:
            issues.append("Missing Open Graph title")
        if not result.open_graph.image:
            issues.append("Missing Open Graph image")
        
        # Twitter Card issues
        if not result.twitter_card.card_type:
            issues.append("Missing Twitter Card type")
        
        # Structured data
        if not result.structured_data:
            issues.append("No structured data found")
        
        # Word count
        if result.word_count < 300:
            issues.append("Low word count (< 300 words)")
        
        return issues
    
    def _calculate_score(self, result: SEOAnalysisResult) -> float:
        """Calculate SEO score based on findings."""
        score = 100.0
        
        # Deduct points for each issue
        score -= len(result.issues) * 5
        
        # Bonus for good practices
        if result.canonical_url:
            score += 2
        if result.open_graph.title and result.open_graph.image:
            score += 3
        if result.twitter_card.card_type:
            score += 2
        if result.structured_data:
            score += 5
        if result.hreflang:
            score += 3
        
        return max(0, min(100, score))
    
    def generate_meta_tags(self, result: SEOAnalysisResult) -> str:
        """
        Generate HTML meta tags from analysis result.
        
        Args:
            result: SEOAnalysisResult to convert
            
        Returns:
            HTML string with meta tags
        """
        lines = []
        
        # Basic meta tags
        if result.title:
            lines.append(f'<title>{result.title}</title>')
        
        if result.meta_description:
            lines.append(f'<meta name="description" content="{result.meta_description}">')
        
        if result.canonical_url:
            lines.append(f'<link rel="canonical" href="{result.canonical_url}">')
        
        if result.robots:
            lines.append(f'<meta name="robots" content="{result.robots}">')
        
        # Open Graph
        if result.open_graph:
            og = result.open_graph
            if og.title:
                lines.append(f'<meta property="og:title" content="{og.title}">')
            if og.description:
                lines.append(f'<meta property="og:description" content="{og.description}">')
            if og.url:
                lines.append(f'<meta property="og:url" content="{og.url}">')
            if og.image:
                lines.append(f'<meta property="og:image" content="{og.image}">')
            if og.type:
                lines.append(f'<meta property="og:type" content="{og.type}">')
        
        # Twitter Card
        if result.twitter_card:
            tc = result.twitter_card
            if tc.card_type:
                lines.append(f'<meta name="twitter:card" content="{tc.card_type}">')
            if tc.title:
                lines.append(f'<meta name="twitter:title" content="{tc.title}">')
            if tc.description:
                lines.append(f'<meta name="twitter:description" content="{tc.description}">')
            if tc.image:
                lines.append(f'<meta name="twitter:image" content="{tc.image}">')
        
        # Hreflang
        for hl in result.hreflang:
            lines.append(f'<link rel="alternate" hreflang="{hl["lang"]}" href="{hl["url"]}">')
        
        return '\n'.join(lines)
