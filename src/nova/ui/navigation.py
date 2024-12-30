"""Navigation UI components and utilities."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Set
import re

from jinja2 import Template

from nova.models.links import LinkContext
from nova.models.link_map import NavigationPath, NavigationNode


@dataclass
class NavigationHeader:
    """Navigation header for a document."""
    title: str
    file_path: str
    section_id: Optional[str] = None
    parent_path: Optional[str] = None
    breadcrumbs: List[str] = None
    quick_links: List[LinkContext] = None


class NavigationRenderer:
    """Renders navigation elements for documents."""
    
    # Template for navigation header
    HEADER_TEMPLATE = """
    <div class="nova-nav-header">
        <div class="nova-breadcrumbs">
            {% for crumb in breadcrumbs %}
            <span class="nova-breadcrumb">{{ crumb }}</span>
            {% if not loop.last %}<span class="nova-breadcrumb-sep">›</span>{% endif %}
            {% endfor %}
        </div>
        <h1 class="nova-title">{{ title }}</h1>
        {% if quick_links %}
        <div class="nova-quick-links">
            <span class="nova-quick-links-label">Quick Links:</span>
            {% for link in quick_links %}
            <a href="{{ link.target_file }}{% if link.target_section %}#{{ link.target_section }}{% endif %}"
               class="nova-quick-link"
               title="{{ link.context if link.context else '' }}">
                {{ link.title if link.title else link.target_file }}
            </a>
            {% endfor %}
        </div>
        {% endif %}
    </div>
    """
    
    # Template for context tooltip
    TOOLTIP_TEMPLATE = """
    <div class="nova-tooltip">
        <div class="nova-tooltip-header">
            <span class="nova-tooltip-title">{{ title }}</span>
            <span class="nova-tooltip-type">{{ link_type }}</span>
        </div>
        {% if context %}
        <div class="nova-tooltip-context">{{ context }}</div>
        {% endif %}
        {% if navigation_path %}
        <div class="nova-tooltip-path">
            Path: {{ navigation_path }}
        </div>
        {% endif %}
    </div>
    """
    
    # CSS styles for navigation elements
    CSS_STYLES = """
    /* Navigation Header Styles */
    .nova-nav-header {
        padding: 1rem;
        margin-bottom: 2rem;
        background: #f8f9fa;
        border-bottom: 1px solid #e9ecef;
    }
    
    .nova-breadcrumbs {
        font-size: 0.9rem;
        color: #6c757d;
        margin-bottom: 0.5rem;
    }
    
    .nova-breadcrumb {
        color: #495057;
        text-decoration: none;
    }
    
    .nova-breadcrumb-sep {
        margin: 0 0.5rem;
        color: #adb5bd;
    }
    
    .nova-title {
        margin: 0;
        color: #212529;
        font-size: 2rem;
    }
    
    .nova-quick-links {
        margin-top: 1rem;
        font-size: 0.9rem;
    }
    
    .nova-quick-links-label {
        color: #6c757d;
        margin-right: 0.5rem;
    }
    
    .nova-quick-link {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        margin: 0 0.25rem;
        color: #0d6efd;
        text-decoration: none;
        background: #e9ecef;
        border-radius: 0.25rem;
    }
    
    .nova-quick-link:hover {
        background: #dee2e6;
        text-decoration: underline;
    }
    
    /* Tooltip Styles */
    .nova-tooltip {
        position: absolute;
        z-index: 1000;
        max-width: 300px;
        padding: 0.5rem;
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 0.25rem;
        box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
        font-size: 0.875rem;
    }
    
    .nova-tooltip-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    
    .nova-tooltip-title {
        font-weight: bold;
        color: #212529;
    }
    
    .nova-tooltip-type {
        font-size: 0.75rem;
        color: #6c757d;
        padding: 0.125rem 0.25rem;
        background: #f8f9fa;
        border-radius: 0.25rem;
    }
    
    .nova-tooltip-context {
        color: #495057;
        margin-bottom: 0.5rem;
        white-space: pre-wrap;
    }
    
    .nova-tooltip-path {
        font-size: 0.75rem;
        color: #6c757d;
        padding-top: 0.5rem;
        border-top: 1px solid #e9ecef;
    }
    """
    
    def __init__(self):
        """Initialize navigation renderer."""
        self.header_template = Template(self.HEADER_TEMPLATE)
        self.tooltip_template = Template(self.TOOLTIP_TEMPLATE)
    
    def render_header(self, header: NavigationHeader) -> str:
        """Render a navigation header.
        
        Args:
            header: Navigation header to render
            
        Returns:
            HTML string for the header
        """
        # Build breadcrumbs if not provided
        if header.breadcrumbs is None:
            header.breadcrumbs = self._build_breadcrumbs(header)
        
        return self.header_template.render(
            title=header.title,
            breadcrumbs=header.breadcrumbs,
            quick_links=header.quick_links
        )
    
    def render_tooltip(
        self,
        link: LinkContext,
        navigation_path: Optional[NavigationPath] = None
    ) -> str:
        """Render a context tooltip for a link.
        
        Args:
            link: Link to render tooltip for
            navigation_path: Optional navigation path to show
            
        Returns:
            HTML string for the tooltip
        """
        path_str = None
        if navigation_path:
            path_str = " → ".join(
                node.title if node.title else node.file_path
                for node in navigation_path.nodes
            )
        
        return self.tooltip_template.render(
            title=link.title if link.title else link.target_file,
            link_type=link.link_type.value if link.link_type else "link",
            context=link.context,
            navigation_path=path_str
        )
    
    def _build_breadcrumbs(self, header: NavigationHeader) -> List[str]:
        """Build breadcrumbs for a header.
        
        Args:
            header: Navigation header to build breadcrumbs for
            
        Returns:
            List of breadcrumb strings
        """
        breadcrumbs = []
        
        # Add parent path if provided
        if header.parent_path:
            parent = Path(header.parent_path)
            breadcrumbs.extend(part for part in parent.parts if part)
        
        # Add current file
        current = Path(header.file_path)
        breadcrumbs.append(current.stem)
        
        # Add section if provided
        if header.section_id:
            breadcrumbs.append(header.section_id)
        
        return breadcrumbs


def inject_navigation_elements(content: str, header: NavigationHeader) -> str:
    """Inject navigation elements into document content.
    
    Args:
        content: Document content to inject into
        header: Navigation header to inject
        
    Returns:
        Content with navigation elements injected
    """
    renderer = NavigationRenderer()
    nav_header = renderer.render_header(header)
    
    # Extract the main content without any existing navigation elements
    main_content = content
    if "<style>" in content:
        style_end = content.find("</style>")
        if style_end != -1:
            main_content = content[style_end + 8:].strip()
    
    if '<div class="nova-nav-header">' in main_content:
        nav_end = main_content.find('</div>', main_content.find('<div class="nova-nav-header">'))
        if nav_end != -1:
            main_content = main_content[nav_end + 6:].strip()
    
    # Add CSS styles if not already present
    if "<style>" not in content:
        content = f"<style>{NavigationRenderer.CSS_STYLES}</style>\n"
    else:
        content = ""
    
    # Add navigation header after any frontmatter
    if main_content.startswith("---"):
        # Find end of frontmatter
        end = main_content.find("---", 3)
        if end != -1:
            return f"{content}{main_content[:end+3]}\n{nav_header}\n{main_content[end+3:]}"
    
    # No frontmatter, just add at start
    return f"{content}{nav_header}\n{main_content}"


def add_tooltips_to_links(content: str, links: List[LinkContext], paths: Dict[str, NavigationPath] = None) -> str:
    """Add tooltips to links in content.
    
    Args:
        content: Document content to add tooltips to
        links: List of links to add tooltips for
        paths: Optional map of target files to navigation paths
        
    Returns:
        Content with tooltips added to links
    """
    renderer = NavigationRenderer()
    
    for link in links:
        # Find the link in the content
        pattern = rf'\[([^\]]+)\]\({re.escape(link.target_file)}'
        if link.target_section:
            pattern += rf'#{re.escape(link.target_section)}'
        pattern += r'\)'
        
        # Get navigation path if available
        path = paths.get(link.target_file) if paths else None
        
        # Generate tooltip
        tooltip = renderer.render_tooltip(link, path)
        
        # Replace with link + tooltip
        replacement = rf'<span class="nova-link-wrapper" data-tooltip="{tooltip}">\g<0></span>'
        content = re.sub(pattern, replacement, content)
    
    return content 