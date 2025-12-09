"""
Accessibility checker module for analyzing website accessibility.

Checks for common accessibility issues and WCAG compliance.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from enum import Enum

from bs4 import BeautifulSoup, Tag

from ..utils.log import get_logger


class IssueLevel(Enum):
    """Severity level of accessibility issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class WCAGLevel(Enum):
    """WCAG compliance levels."""
    A = "A"
    AA = "AA"
    AAA = "AAA"


@dataclass
class AccessibilityIssue:
    """Represents an accessibility issue found."""
    rule_id: str
    description: str
    level: IssueLevel
    wcag_criteria: str
    wcag_level: WCAGLevel
    element: Optional[str] = None
    selector: Optional[str] = None
    recommendation: Optional[str] = None
    count: int = 1


@dataclass
class AccessibilityResult:
    """Result of accessibility analysis."""
    issues: List[AccessibilityIssue] = field(default_factory=list)
    issue_count: int = 0
    errors_count: int = 0
    warnings_count: int = 0
    passed_checks: List[str] = field(default_factory=list)
    score: float = 100.0
    wcag_level: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)


class AccessibilityChecker:
    """
    Checks web pages for accessibility issues.
    
    Analyzes HTML for common accessibility problems and
    WCAG guideline violations.
    """
    
    def __init__(self):
        """Initialize the accessibility checker."""
        self.logger = get_logger("accessibility")
    
    def check(self, html: str) -> AccessibilityResult:
        """
        Check HTML content for accessibility issues.
        
        Args:
            html: HTML content to analyze
            
        Returns:
            AccessibilityResult with found issues
        """
        result = AccessibilityResult()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        
        # Run all checks
        self._check_images(soup, result)
        self._check_links(soup, result)
        self._check_forms(soup, result)
        self._check_headings(soup, result)
        self._check_language(soup, result)
        self._check_landmarks(soup, result)
        self._check_tables(soup, result)
        self._check_color_contrast_indicators(soup, result)
        self._check_focus_indicators(soup, result)
        self._check_aria(soup, result)
        self._check_skip_links(soup, result)
        self._check_document_structure(soup, result)
        
        # Calculate counts
        result.issue_count = len(result.issues)
        result.errors_count = sum(
            1 for i in result.issues if i.level == IssueLevel.ERROR
        )
        result.warnings_count = sum(
            1 for i in result.issues if i.level == IssueLevel.WARNING
        )
        
        # Calculate score
        result.score = self._calculate_score(result)
        
        # Determine WCAG level
        result.wcag_level = self._determine_wcag_level(result)
        
        # Generate summary
        result.summary = self._generate_summary(soup, result)
        
        return result
    
    def _check_images(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check images for accessibility issues."""
        images = soup.find_all('img')
        images_without_alt = 0
        images_with_empty_alt = 0
        
        for img in images:
            alt = img.get('alt')
            
            if alt is None:
                images_without_alt += 1
                result.issues.append(AccessibilityIssue(
                    rule_id="img-alt-missing",
                    description="Image is missing alt attribute",
                    level=IssueLevel.ERROR,
                    wcag_criteria="1.1.1",
                    wcag_level=WCAGLevel.A,
                    element=str(img)[:100],
                    selector=self._build_selector(img),
                    recommendation="Add alt attribute with descriptive text"
                ))
            elif alt.strip() == "":
                # Empty alt is okay for decorative images
                images_with_empty_alt += 1
        
        # Check for decorative images without empty alt
        if images and images_without_alt == 0:
            result.passed_checks.append("All images have alt attributes")
    
    def _check_links(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check links for accessibility issues."""
        links = soup.find_all('a')
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            aria_label = link.get('aria-label', '')
            
            # Check for empty links
            if not text and not aria_label:
                img = link.find('img')
                if not img or not img.get('alt'):
                    result.issues.append(AccessibilityIssue(
                        rule_id="link-empty",
                        description="Link has no accessible text",
                        level=IssueLevel.ERROR,
                        wcag_criteria="2.4.4",
                        wcag_level=WCAGLevel.A,
                        element=str(link)[:100],
                        selector=self._build_selector(link),
                        recommendation="Add link text or aria-label"
                    ))
            
            # Check for generic link text
            generic_texts = {'click here', 'read more', 'learn more', 'here', 'more'}
            if text.lower() in generic_texts:
                result.issues.append(AccessibilityIssue(
                    rule_id="link-generic-text",
                    description=f"Link has generic text: '{text}'",
                    level=IssueLevel.WARNING,
                    wcag_criteria="2.4.4",
                    wcag_level=WCAGLevel.A,
                    element=str(link)[:100],
                    recommendation="Use descriptive link text"
                ))
            
            # Check for target="_blank" without rel
            if link.get('target') == '_blank':
                rel = link.get('rel', [])
                if isinstance(rel, str):
                    rel = rel.split()
                if 'noopener' not in rel and 'noreferrer' not in rel:
                    result.issues.append(AccessibilityIssue(
                        rule_id="link-target-blank",
                        description="Link opens in new tab without security attributes",
                        level=IssueLevel.WARNING,
                        wcag_criteria="3.2.5",
                        wcag_level=WCAGLevel.AAA,
                        element=str(link)[:100],
                        recommendation="Add rel='noopener noreferrer' for security"
                    ))
    
    def _check_forms(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check forms for accessibility issues."""
        # Check inputs for labels
        inputs = soup.find_all(['input', 'select', 'textarea'])
        
        for input_elem in inputs:
            input_type = input_elem.get('type', 'text')
            
            # Skip hidden and button inputs
            if input_type in {'hidden', 'submit', 'button', 'reset'}:
                continue
            
            input_id = input_elem.get('id')
            aria_label = input_elem.get('aria-label')
            aria_labelledby = input_elem.get('aria-labelledby')
            
            has_label = False
            
            # Check for associated label
            if input_id:
                label = soup.find('label', attrs={'for': input_id})
                if label:
                    has_label = True
            
            # Check for aria-label or aria-labelledby
            if aria_label or aria_labelledby:
                has_label = True
            
            # Check for wrapping label
            parent = input_elem.parent
            if parent and parent.name == 'label':
                has_label = True
            
            if not has_label:
                result.issues.append(AccessibilityIssue(
                    rule_id="form-input-no-label",
                    description="Form input has no associated label",
                    level=IssueLevel.ERROR,
                    wcag_criteria="1.3.1",
                    wcag_level=WCAGLevel.A,
                    element=str(input_elem)[:100],
                    selector=self._build_selector(input_elem),
                    recommendation="Add a <label> element with 'for' attribute or aria-label"
                ))
        
        # Check for form error handling
        forms = soup.find_all('form')
        for form in forms:
            aria_describedby = form.get('aria-describedby')
            if not aria_describedby:
                # Check if there's error handling mechanism
                error_elements = form.find_all(class_=lambda c: c and 'error' in c.lower() if c else False)
                if not error_elements:
                    result.issues.append(AccessibilityIssue(
                        rule_id="form-no-error-handling",
                        description="Form may lack accessible error handling",
                        level=IssueLevel.INFO,
                        wcag_criteria="3.3.1",
                        wcag_level=WCAGLevel.A,
                        element=str(form)[:100],
                        recommendation="Add accessible error messages linked via aria-describedby"
                    ))
    
    def _check_headings(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check heading structure for accessibility."""
        headings = []
        for i in range(1, 7):
            for h in soup.find_all(f'h{i}'):
                headings.append((i, h))
        
        if not headings:
            result.issues.append(AccessibilityIssue(
                rule_id="heading-none",
                description="Page has no headings",
                level=IssueLevel.WARNING,
                wcag_criteria="1.3.1",
                wcag_level=WCAGLevel.A,
                recommendation="Add heading structure to organize content"
            ))
            return
        
        # Check for h1
        h1_count = len([h for h in headings if h[0] == 1])
        if h1_count == 0:
            result.issues.append(AccessibilityIssue(
                rule_id="heading-no-h1",
                description="Page has no h1 heading",
                level=IssueLevel.ERROR,
                wcag_criteria="1.3.1",
                wcag_level=WCAGLevel.A,
                recommendation="Add a main h1 heading"
            ))
        elif h1_count > 1:
            result.issues.append(AccessibilityIssue(
                rule_id="heading-multiple-h1",
                description=f"Page has {h1_count} h1 headings",
                level=IssueLevel.WARNING,
                wcag_criteria="1.3.1",
                wcag_level=WCAGLevel.A,
                recommendation="Consider having only one h1 per page"
            ))
        
        # Check heading order
        prev_level = 0
        for level, h in headings:
            if level > prev_level + 1 and prev_level > 0:
                result.issues.append(AccessibilityIssue(
                    rule_id="heading-skip-level",
                    description=f"Heading level skipped from h{prev_level} to h{level}",
                    level=IssueLevel.WARNING,
                    wcag_criteria="1.3.1",
                    wcag_level=WCAGLevel.A,
                    element=str(h)[:100],
                    recommendation="Don't skip heading levels"
                ))
            prev_level = level
        
        # Check for empty headings
        for level, h in headings:
            if not h.get_text(strip=True):
                result.issues.append(AccessibilityIssue(
                    rule_id="heading-empty",
                    description=f"Empty h{level} heading",
                    level=IssueLevel.ERROR,
                    wcag_criteria="1.3.1",
                    wcag_level=WCAGLevel.A,
                    element=str(h)[:100],
                    recommendation="Add content to heading or remove it"
                ))
    
    def _check_language(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check for language attributes."""
        html = soup.find('html')
        
        if html:
            lang = html.get('lang')
            if not lang:
                result.issues.append(AccessibilityIssue(
                    rule_id="html-no-lang",
                    description="HTML element is missing lang attribute",
                    level=IssueLevel.ERROR,
                    wcag_criteria="3.1.1",
                    wcag_level=WCAGLevel.A,
                    recommendation="Add lang attribute to html element"
                ))
            else:
                result.passed_checks.append("HTML has lang attribute")
    
    def _check_landmarks(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check for ARIA landmarks."""
        has_main = bool(soup.find('main') or soup.find(role='main'))
        has_nav = bool(soup.find('nav') or soup.find(role='navigation'))
        has_banner = bool(soup.find('header') or soup.find(role='banner'))
        has_contentinfo = bool(soup.find('footer') or soup.find(role='contentinfo'))
        
        if not has_main:
            result.issues.append(AccessibilityIssue(
                rule_id="landmark-no-main",
                description="Page has no main landmark",
                level=IssueLevel.WARNING,
                wcag_criteria="1.3.1",
                wcag_level=WCAGLevel.A,
                recommendation="Add <main> element or role='main'"
            ))
        
        # Check for multiple nav without labels
        navs = soup.find_all('nav')
        if len(navs) > 1:
            for nav in navs:
                if not nav.get('aria-label') and not nav.get('aria-labelledby'):
                    result.issues.append(AccessibilityIssue(
                        rule_id="landmark-nav-no-label",
                        description="Multiple nav elements without unique labels",
                        level=IssueLevel.WARNING,
                        wcag_criteria="1.3.1",
                        wcag_level=WCAGLevel.A,
                        element=str(nav)[:100],
                        recommendation="Add aria-label to distinguish nav elements"
                    ))
                    break
    
    def _check_tables(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check tables for accessibility."""
        tables = soup.find_all('table')
        
        for table in tables:
            # Check for caption or summary
            caption = table.find('caption')
            summary = table.get('summary')
            aria_label = table.get('aria-label')
            aria_labelledby = table.get('aria-labelledby')
            
            if not caption and not summary and not aria_label and not aria_labelledby:
                result.issues.append(AccessibilityIssue(
                    rule_id="table-no-caption",
                    description="Table has no caption or accessible name",
                    level=IssueLevel.WARNING,
                    wcag_criteria="1.3.1",
                    wcag_level=WCAGLevel.A,
                    element=str(table)[:100],
                    recommendation="Add <caption> or aria-label"
                ))
            
            # Check for header cells
            th_cells = table.find_all('th')
            if not th_cells:
                result.issues.append(AccessibilityIssue(
                    rule_id="table-no-headers",
                    description="Table has no header cells",
                    level=IssueLevel.ERROR,
                    wcag_criteria="1.3.1",
                    wcag_level=WCAGLevel.A,
                    element=str(table)[:100],
                    recommendation="Add <th> elements for header cells"
                ))
            
            # Check th scope
            for th in th_cells:
                scope = th.get('scope')
                if not scope:
                    result.issues.append(AccessibilityIssue(
                        rule_id="table-th-no-scope",
                        description="Table header cell missing scope attribute",
                        level=IssueLevel.WARNING,
                        wcag_criteria="1.3.1",
                        wcag_level=WCAGLevel.A,
                        element=str(th)[:100],
                        recommendation="Add scope='col' or scope='row'"
                    ))
                    break
    
    def _check_color_contrast_indicators(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check for color contrast issues (heuristic)."""
        # This is a simplified check - full contrast checking requires computed styles
        
        # Check for color-only information indicators
        elements_with_color = soup.find_all(
            style=lambda s: s and ('color:' in s.lower() or 'background' in s.lower()) if s else False
        )
        
        # This is informational only
        if len(elements_with_color) > 0:
            result.issues.append(AccessibilityIssue(
                rule_id="color-contrast-check",
                description="Page uses color styling - verify color contrast meets WCAG requirements",
                level=IssueLevel.INFO,
                wcag_criteria="1.4.3",
                wcag_level=WCAGLevel.AA,
                recommendation="Ensure text has at least 4.5:1 contrast ratio"
            ))
    
    def _check_focus_indicators(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check for focus indicator issues."""
        # Check for outline:none or outline:0 which removes focus indicators
        style_content = ""
        
        for style in soup.find_all('style'):
            if style.string:
                style_content += style.string
        
        style_content_lower = style_content.lower()
        if 'outline:none' in style_content_lower or 'outline: none' in style_content_lower or 'outline:0' in style_content_lower:
            result.issues.append(AccessibilityIssue(
                rule_id="focus-outline-removed",
                description="Focus outline may be removed in styles",
                level=IssueLevel.WARNING,
                wcag_criteria="2.4.7",
                wcag_level=WCAGLevel.AA,
                recommendation="Ensure interactive elements have visible focus indicators"
            ))
    
    def _check_aria(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check ARIA usage."""
        # Check for invalid ARIA roles
        valid_roles = {
            'alert', 'alertdialog', 'application', 'article', 'banner',
            'button', 'cell', 'checkbox', 'columnheader', 'combobox',
            'complementary', 'contentinfo', 'definition', 'dialog',
            'directory', 'document', 'feed', 'figure', 'form', 'grid',
            'gridcell', 'group', 'heading', 'img', 'link', 'list',
            'listbox', 'listitem', 'log', 'main', 'marquee', 'math',
            'menu', 'menubar', 'menuitem', 'menuitemcheckbox',
            'menuitemradio', 'navigation', 'none', 'note', 'option',
            'presentation', 'progressbar', 'radio', 'radiogroup',
            'region', 'row', 'rowgroup', 'rowheader', 'scrollbar',
            'search', 'searchbox', 'separator', 'slider', 'spinbutton',
            'status', 'switch', 'tab', 'table', 'tablist', 'tabpanel',
            'term', 'textbox', 'timer', 'toolbar', 'tooltip', 'tree',
            'treegrid', 'treeitem'
        }
        
        elements_with_role = soup.find_all(role=True)
        for elem in elements_with_role:
            role = elem.get('role', '').lower()
            if role and role not in valid_roles:
                result.issues.append(AccessibilityIssue(
                    rule_id="aria-invalid-role",
                    description=f"Invalid ARIA role: '{role}'",
                    level=IssueLevel.ERROR,
                    wcag_criteria="4.1.2",
                    wcag_level=WCAGLevel.A,
                    element=str(elem)[:100],
                    recommendation="Use a valid ARIA role"
                ))
        
        # Check for aria-hidden on focusable elements
        hidden_elements = soup.find_all(attrs={'aria-hidden': 'true'})
        for elem in hidden_elements:
            if elem.name in {'a', 'button', 'input', 'select', 'textarea'}:
                result.issues.append(AccessibilityIssue(
                    rule_id="aria-hidden-focusable",
                    description="aria-hidden='true' on focusable element",
                    level=IssueLevel.ERROR,
                    wcag_criteria="4.1.2",
                    wcag_level=WCAGLevel.A,
                    element=str(elem)[:100],
                    recommendation="Don't hide focusable elements from assistive technology"
                ))
    
    def _check_skip_links(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check for skip links."""
        first_links = soup.find_all('a')[:5]
        has_skip_link = False
        
        skip_indicators = ['skip', 'main', 'content', 'navigation']
        
        for link in first_links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            if href.startswith('#') and any(ind in text for ind in skip_indicators):
                has_skip_link = True
                break
        
        if not has_skip_link:
            result.issues.append(AccessibilityIssue(
                rule_id="skip-link-missing",
                description="Page may be missing skip navigation link",
                level=IssueLevel.WARNING,
                wcag_criteria="2.4.1",
                wcag_level=WCAGLevel.A,
                recommendation="Add a 'Skip to main content' link at the start of the page"
            ))
    
    def _check_document_structure(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> None:
        """Check overall document structure."""
        # Check for title
        title = soup.find('title')
        if not title or not title.get_text(strip=True):
            result.issues.append(AccessibilityIssue(
                rule_id="document-no-title",
                description="Page is missing a title",
                level=IssueLevel.ERROR,
                wcag_criteria="2.4.2",
                wcag_level=WCAGLevel.A,
                recommendation="Add a descriptive <title> element"
            ))
        else:
            result.passed_checks.append("Page has title")
        
        # Check for viewport meta
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if viewport:
            content = viewport.get('content', '')
            if 'user-scalable=no' in content.lower() or 'maximum-scale=1' in content:
                result.issues.append(AccessibilityIssue(
                    rule_id="viewport-zoom-disabled",
                    description="Page prevents zooming",
                    level=IssueLevel.ERROR,
                    wcag_criteria="1.4.4",
                    wcag_level=WCAGLevel.AA,
                    recommendation="Allow users to zoom the page"
                ))
    
    def _build_selector(self, elem: Tag) -> str:
        """Build a CSS selector for an element."""
        if not isinstance(elem, Tag):
            return ""
        
        tag = elem.name
        
        if elem.get('id'):
            return f"{tag}#{elem['id']}"
        
        classes = elem.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()
        
        if classes:
            return f"{tag}.{'.'.join(classes[:2])}"
        
        return tag
    
    def _calculate_score(self, result: AccessibilityResult) -> float:
        """Calculate accessibility score."""
        if not result.issues:
            return 100.0
        
        # Weight by severity
        error_penalty = result.errors_count * 5
        warning_penalty = result.warnings_count * 2
        info_penalty = sum(1 for i in result.issues if i.level == IssueLevel.INFO)
        
        total_penalty = error_penalty + warning_penalty + info_penalty
        score = max(0, 100 - total_penalty)
        
        return round(score, 1)
    
    def _determine_wcag_level(self, result: AccessibilityResult) -> str:
        """Determine highest WCAG compliance level."""
        level_a_errors = [
            i for i in result.issues
            if i.wcag_level == WCAGLevel.A and i.level == IssueLevel.ERROR
        ]
        
        level_aa_errors = [
            i for i in result.issues
            if i.wcag_level == WCAGLevel.AA and i.level == IssueLevel.ERROR
        ]
        
        if level_a_errors:
            return "Below Level A"
        elif level_aa_errors:
            return "Level A"
        else:
            return "Level AA (tentative)"
    
    def _generate_summary(
        self,
        soup: BeautifulSoup,
        result: AccessibilityResult
    ) -> Dict[str, Any]:
        """Generate a summary of accessibility analysis."""
        return {
            'total_issues': result.issue_count,
            'errors': result.errors_count,
            'warnings': result.warnings_count,
            'passed_checks': len(result.passed_checks),
            'score': result.score,
            'wcag_level': result.wcag_level,
            'has_images': len(soup.find_all('img')),
            'has_links': len(soup.find_all('a')),
            'has_forms': len(soup.find_all('form')),
            'has_tables': len(soup.find_all('table')),
            'semantic_elements': {
                'header': bool(soup.find('header')),
                'main': bool(soup.find('main')),
                'footer': bool(soup.find('footer')),
                'nav': bool(soup.find('nav')),
                'article': bool(soup.find('article')),
                'section': bool(soup.find('section')),
                'aside': bool(soup.find('aside')),
            }
        }
