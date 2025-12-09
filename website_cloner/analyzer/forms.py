"""
Form analyzer module for extracting form information.

Extracts form fields, validation rules, and structure.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from bs4 import BeautifulSoup, Tag

from ..utils.log import get_logger


@dataclass
class FormField:
    """Represents a form field."""
    name: str
    field_type: str  # text, email, password, select, textarea, etc.
    label: Optional[str] = None
    placeholder: Optional[str] = None
    required: bool = False
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    options: List[str] = field(default_factory=list)  # For select/radio
    default_value: Optional[str] = None
    autocomplete: Optional[str] = None
    validation_message: Optional[str] = None
    aria_label: Optional[str] = None
    html: str = ""


@dataclass
class FormInfo:
    """Information about a form."""
    form_id: Optional[str] = None
    form_name: Optional[str] = None
    action: Optional[str] = None
    method: str = "get"
    enctype: Optional[str] = None
    fields: List[FormField] = field(default_factory=list)
    submit_button: Optional[Dict[str, str]] = None
    has_csrf: bool = False
    has_captcha: bool = False
    html: str = ""


@dataclass
class FormAnalysisResult:
    """Result of form analysis."""
    forms: List[FormInfo] = field(default_factory=list)
    total_forms: int = 0
    total_fields: int = 0
    form_types: Dict[str, int] = field(default_factory=dict)
    field_types: Dict[str, int] = field(default_factory=dict)


class FormAnalyzer:
    """
    Analyzes forms in web pages.
    
    Extracts form structure, fields, validation rules, and other information.
    """
    
    # Input types
    INPUT_TYPES = {
        'text', 'email', 'password', 'number', 'tel', 'url',
        'search', 'date', 'time', 'datetime-local', 'month',
        'week', 'color', 'range', 'file', 'hidden', 'checkbox',
        'radio', 'submit', 'button', 'reset', 'image'
    }
    
    def __init__(self):
        """Initialize the form analyzer."""
        self.logger = get_logger("forms")
    
    def analyze(self, html: str) -> FormAnalysisResult:
        """
        Analyze forms in HTML content.
        
        Args:
            html: HTML content to analyze
            
        Returns:
            FormAnalysisResult with extracted form information
        """
        result = FormAnalysisResult()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        
        forms = soup.find_all('form')
        
        for form in forms:
            form_info = self._analyze_form(form, soup)
            result.forms.append(form_info)
            
            # Count fields by type
            for fld in form_info.fields:
                fld_type = fld.field_type
                result.field_types[fld_type] = result.field_types.get(fld_type, 0) + 1
            
            # Determine form type
            form_type = self._determine_form_type(form_info)
            result.form_types[form_type] = result.form_types.get(form_type, 0) + 1
        
        result.total_forms = len(result.forms)
        result.total_fields = sum(len(f.fields) for f in result.forms)
        
        return result
    
    def _analyze_form(self, form: Tag, soup: BeautifulSoup) -> FormInfo:
        """Analyze a single form element."""
        form_info = FormInfo(
            form_id=form.get('id'),
            form_name=form.get('name'),
            action=form.get('action', ''),
            method=form.get('method', 'get').lower(),
            enctype=form.get('enctype'),
            html=str(form)[:2000]
        )
        
        # Extract all form fields
        form_info.fields = self._extract_fields(form, soup)
        
        # Find submit button
        submit = form.find('button', type='submit') or form.find('input', type='submit')
        if submit:
            form_info.submit_button = {
                'text': submit.get_text(strip=True) if submit.name == 'button' else submit.get('value', 'Submit'),
                'type': submit.name
            }
        
        # Check for CSRF token
        csrf_names = {'csrf', 'csrf_token', '_token', 'authenticity_token', '__RequestVerificationToken'}
        for name in csrf_names:
            if form.find('input', attrs={'name': name}):
                form_info.has_csrf = True
                break
        
        # Check for CAPTCHA
        captcha_indicators = ['recaptcha', 'captcha', 'hcaptcha', 'g-recaptcha']
        form_str = str(form).lower()
        for indicator in captcha_indicators:
            if indicator in form_str:
                form_info.has_captcha = True
                break
        
        return form_info
    
    def _extract_fields(self, form: Tag, soup: BeautifulSoup) -> List[FormField]:
        """Extract all fields from a form."""
        fields = []
        
        # Input elements
        for input_elem in form.find_all('input'):
            input_type = input_elem.get('type', 'text').lower()
            
            # Skip hidden, submit, button types for main field list
            if input_type in {'hidden', 'submit', 'button', 'reset', 'image'}:
                continue
            
            field = self._create_field_from_input(input_elem, soup)
            fields.append(field)
        
        # Select elements
        for select in form.find_all('select'):
            field = self._create_field_from_select(select, soup)
            fields.append(field)
        
        # Textarea elements
        for textarea in form.find_all('textarea'):
            field = self._create_field_from_textarea(textarea, soup)
            fields.append(field)
        
        return fields
    
    def _create_field_from_input(
        self,
        input_elem: Tag,
        soup: BeautifulSoup
    ) -> FormField:
        """Create FormField from an input element."""
        input_type = input_elem.get('type', 'text').lower()
        name = input_elem.get('name', '')
        input_id = input_elem.get('id')
        
        # Find associated label
        label = None
        if input_id:
            label_elem = soup.find('label', attrs={'for': input_id})
            if label_elem:
                label = label_elem.get_text(strip=True)
        
        # For radio/checkbox, get options
        options = []
        if input_type in {'radio', 'checkbox'}:
            group_inputs = soup.find_all('input', attrs={'name': name})
            for inp in group_inputs:
                value = inp.get('value', '')
                inp_label = None
                inp_id = inp.get('id')
                if inp_id:
                    inp_label_elem = soup.find('label', attrs={'for': inp_id})
                    if inp_label_elem:
                        inp_label = inp_label_elem.get_text(strip=True)
                options.append(inp_label or value)
        
        return FormField(
            name=name,
            field_type=input_type,
            label=label,
            placeholder=input_elem.get('placeholder'),
            required=input_elem.has_attr('required'),
            pattern=input_elem.get('pattern'),
            min_length=self._parse_int(input_elem.get('minlength')),
            max_length=self._parse_int(input_elem.get('maxlength')),
            min_value=input_elem.get('min'),
            max_value=input_elem.get('max'),
            options=options,
            default_value=input_elem.get('value'),
            autocomplete=input_elem.get('autocomplete'),
            aria_label=input_elem.get('aria-label'),
            html=str(input_elem)
        )
    
    def _create_field_from_select(
        self,
        select: Tag,
        soup: BeautifulSoup
    ) -> FormField:
        """Create FormField from a select element."""
        name = select.get('name', '')
        select_id = select.get('id')
        
        # Find associated label
        label = None
        if select_id:
            label_elem = soup.find('label', attrs={'for': select_id})
            if label_elem:
                label = label_elem.get_text(strip=True)
        
        # Get options
        options = []
        for option in select.find_all('option'):
            text = option.get_text(strip=True)
            if text:
                options.append(text)
        
        return FormField(
            name=name,
            field_type='select',
            label=label,
            required=select.has_attr('required'),
            options=options,
            aria_label=select.get('aria-label'),
            html=str(select)
        )
    
    def _create_field_from_textarea(
        self,
        textarea: Tag,
        soup: BeautifulSoup
    ) -> FormField:
        """Create FormField from a textarea element."""
        name = textarea.get('name', '')
        textarea_id = textarea.get('id')
        
        # Find associated label
        label = None
        if textarea_id:
            label_elem = soup.find('label', attrs={'for': textarea_id})
            if label_elem:
                label = label_elem.get_text(strip=True)
        
        return FormField(
            name=name,
            field_type='textarea',
            label=label,
            placeholder=textarea.get('placeholder'),
            required=textarea.has_attr('required'),
            min_length=self._parse_int(textarea.get('minlength')),
            max_length=self._parse_int(textarea.get('maxlength')),
            default_value=textarea.get_text(),
            aria_label=textarea.get('aria-label'),
            html=str(textarea)
        )
    
    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Parse an integer value safely."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _determine_form_type(self, form_info: FormInfo) -> str:
        """Determine the type of form based on its fields."""
        field_names = [f.name.lower() for f in form_info.fields if f.name]
        field_types = [f.field_type for f in form_info.fields]
        
        # Check for login form
        has_password = 'password' in field_types
        has_email = 'email' in field_types or any('email' in n for n in field_names)
        has_username = any(n in field_names for n in ['username', 'user', 'login'])
        
        if has_password and (has_email or has_username) and len(form_info.fields) <= 3:
            return 'login'
        
        # Check for registration form
        if has_password and has_email and len(form_info.fields) > 3:
            confirm_password = any('confirm' in n or 'repeat' in n for n in field_names)
            if confirm_password:
                return 'registration'
        
        # Check for search form
        if len(form_info.fields) == 1:
            if 'search' in field_types or any('search' in n or 'q' == n for n in field_names):
                return 'search'
        
        # Check for contact form
        contact_indicators = ['message', 'comment', 'body', 'content', 'subject']
        has_message = any(n in field_names for n in contact_indicators)
        has_textarea = 'textarea' in field_types
        
        if has_email and (has_message or has_textarea):
            return 'contact'
        
        # Check for newsletter/subscribe form
        if has_email and len(form_info.fields) <= 2:
            return 'newsletter'
        
        # Check for checkout/payment form
        payment_indicators = ['card', 'credit', 'payment', 'cvv', 'expiry']
        if any(any(ind in n for ind in payment_indicators) for n in field_names):
            return 'payment'
        
        # Check for address form
        address_indicators = ['address', 'street', 'city', 'zip', 'postal', 'country', 'state']
        address_matches = sum(1 for n in field_names if any(ind in n for ind in address_indicators))
        if address_matches >= 3:
            return 'address'
        
        return 'other'
    
    def generate_form_html(self, form_info: FormInfo) -> str:
        """
        Generate HTML for a form from FormInfo.
        
        Args:
            form_info: FormInfo to convert
            
        Returns:
            HTML string for the form
        """
        lines = []
        
        # Form opening tag
        attrs = []
        if form_info.form_id:
            attrs.append(f'id="{form_info.form_id}"')
        if form_info.form_name:
            attrs.append(f'name="{form_info.form_name}"')
        if form_info.action:
            attrs.append(f'action="{form_info.action}"')
        attrs.append(f'method="{form_info.method}"')
        if form_info.enctype:
            attrs.append(f'enctype="{form_info.enctype}"')
        
        lines.append(f'<form {" ".join(attrs)}>')
        
        # Fields
        for fld in form_info.fields:
            lines.append(self._generate_field_html(fld))
        
        # Submit button
        if form_info.submit_button:
            text = form_info.submit_button.get('text', 'Submit')
            lines.append(f'  <button type="submit">{text}</button>')
        
        lines.append('</form>')
        
        return '\n'.join(lines)
    
    def _generate_field_html(self, fld: FormField) -> str:
        """Generate HTML for a form field."""
        lines = []
        
        # Label
        field_id = fld.name.replace(' ', '_')
        if fld.label:
            lines.append(f'  <label for="{field_id}">{fld.label}</label>')
        
        # Field element
        if fld.field_type == 'textarea':
            attrs = [f'id="{field_id}"', f'name="{fld.name}"']
            if fld.placeholder:
                attrs.append(f'placeholder="{fld.placeholder}"')
            if fld.required:
                attrs.append('required')
            lines.append(f'  <textarea {" ".join(attrs)}>{fld.default_value or ""}</textarea>')
        
        elif fld.field_type == 'select':
            attrs = [f'id="{field_id}"', f'name="{fld.name}"']
            if fld.required:
                attrs.append('required')
            lines.append(f'  <select {" ".join(attrs)}>')
            for opt in fld.options:
                lines.append(f'    <option value="{opt}">{opt}</option>')
            lines.append('  </select>')
        
        elif fld.field_type in {'radio', 'checkbox'}:
            for i, opt in enumerate(fld.options):
                opt_id = f"{field_id}_{i}"
                lines.append(f'  <input type="{fld.field_type}" id="{opt_id}" name="{fld.name}" value="{opt}">')
                lines.append(f'  <label for="{opt_id}">{opt}</label>')
        
        else:
            attrs = [f'type="{fld.field_type}"', f'id="{field_id}"', f'name="{fld.name}"']
            if fld.placeholder:
                attrs.append(f'placeholder="{fld.placeholder}"')
            if fld.required:
                attrs.append('required')
            if fld.pattern:
                attrs.append(f'pattern="{fld.pattern}"')
            if fld.min_length:
                attrs.append(f'minlength="{fld.min_length}"')
            if fld.max_length:
                attrs.append(f'maxlength="{fld.max_length}"')
            if fld.default_value:
                attrs.append(f'value="{fld.default_value}"')
            lines.append(f'  <input {" ".join(attrs)}>')
        
        return '\n'.join(lines)
