"""Unit tests for navigation components."""

import pytest
from pathlib import Path

from nova.models.links import LinkType, LinkContext
from nova.models.link_map import NavigationPath, NavigationNode
from nova.ui.navigation import (
    NavigationHeader,
    NavigationRenderer,
    inject_navigation_elements,
    add_tooltips_to_links
)


@pytest.fixture
def sample_header():
    """Create a sample navigation header."""
    return NavigationHeader(
        title="Test Document",
        file_path="docs/test.md",
        section_id="section-1",
        parent_path="docs",
        breadcrumbs=["docs", "test", "section-1"],
        quick_links=[
            LinkContext(
                source_file="docs/test.md",
                target_file="docs/related.md",
                title="Related Doc"
            )
        ]
    )


@pytest.fixture
def sample_link():
    """Create a sample link context."""
    return LinkContext(
        source_file="docs/test.md",
        target_file="docs/target.md",
        target_section="section-1",
        link_type=LinkType.OUTGOING,
        context="Sample context",
        title="Target Doc"
    )


@pytest.fixture
def sample_path():
    """Create a sample navigation path."""
    return NavigationPath(
        path_type="direct",
        nodes=[
            NavigationNode(
                file_path="docs/test.md",
                section_id="section-1",
                title="Test Doc"
            ),
            NavigationNode(
                file_path="docs/target.md",
                section_id="section-1",
                title="Target Doc"
            )
        ],
        total_links=1,
        bidirectional=False
    )


class TestNavigationHeader:
    """Tests for NavigationHeader."""
    
    def test_header_creation(self, sample_header):
        """Test that NavigationHeader can be created with all fields."""
        assert sample_header.title == "Test Document"
        assert sample_header.file_path == "docs/test.md"
        assert sample_header.section_id == "section-1"
        assert sample_header.parent_path == "docs"
        assert len(sample_header.breadcrumbs) == 3
        assert len(sample_header.quick_links) == 1
    
    def test_header_defaults(self):
        """Test that NavigationHeader has appropriate defaults."""
        header = NavigationHeader(
            title="Test",
            file_path="test.md"
        )
        assert header.section_id is None
        assert header.parent_path is None
        assert header.breadcrumbs is None
        assert header.quick_links is None


class TestNavigationRenderer:
    """Tests for NavigationRenderer."""
    
    @pytest.fixture
    def renderer(self):
        """Create a navigation renderer."""
        return NavigationRenderer()
    
    def test_render_header(self, renderer, sample_header):
        """Test rendering a navigation header."""
        html = renderer.render_header(sample_header)
        
        # Check basic structure
        assert '<div class="nova-nav-header">' in html
        assert '<div class="nova-breadcrumbs">' in html
        assert '<h1 class="nova-title">' in html
        
        # Check content
        assert sample_header.title in html
        for crumb in sample_header.breadcrumbs:
            assert crumb in html
        assert sample_header.quick_links[0].title in html
    
    def test_render_tooltip(self, renderer, sample_link, sample_path):
        """Test rendering a tooltip."""
        html = renderer.render_tooltip(sample_link, sample_path)
        
        # Check basic structure
        assert '<div class="nova-tooltip">' in html
        assert '<div class="nova-tooltip-header">' in html
        
        # Check content
        assert sample_link.title in html
        assert sample_link.context in html
        assert sample_link.link_type.value in html
        
        # Check path display
        for node in sample_path.nodes:
            assert node.title in html
    
    def test_build_breadcrumbs(self, renderer, sample_header):
        """Test building breadcrumbs."""
        # Test with provided breadcrumbs
        assert renderer._build_breadcrumbs(sample_header) == sample_header.breadcrumbs
        
        # Test without provided breadcrumbs
        sample_header.breadcrumbs = None
        breadcrumbs = renderer._build_breadcrumbs(sample_header)
        assert len(breadcrumbs) > 0
        assert Path(sample_header.file_path).stem in breadcrumbs


class TestNavigationInjection:
    """Tests for navigation element injection."""
    
    @pytest.fixture
    def sample_content(self):
        """Create sample document content."""
        return """---
title: Test Document
---
# Test Content
Some test content here."""
    
    def test_inject_navigation_elements(self, sample_header, sample_content):
        """Test injecting navigation elements into content."""
        result = inject_navigation_elements(sample_content, sample_header)
        
        # Check that frontmatter is preserved
        assert result.startswith("---")
        assert "title: Test Document" in result
        
        # Check that navigation is added
        assert '<div class="nova-nav-header">' in result
        assert sample_header.title in result
        
        # Check that original content is preserved
        assert "# Test Content" in result
        assert "Some test content here." in result
        
        # Check that styles are added
        assert "<style>" in result
        assert ".nova-nav-header" in result
    
    def test_inject_without_frontmatter(self, sample_header):
        """Test injecting navigation into content without frontmatter."""
        content = "# Test Content\nSome content."
        result = inject_navigation_elements(content, sample_header)
        
        assert result.startswith('<div class="nova-nav-header">')
        assert "# Test Content" in result


class TestTooltipInjection:
    """Tests for tooltip injection."""
    
    @pytest.fixture
    def sample_content_with_links(self):
        """Create sample content with markdown links."""
        return """# Test Document
See [Target Doc](docs/target.md#section-1) for more info.
Also check [Related](docs/related.md)."""
    
    def test_add_tooltips_to_links(
        self,
        sample_content_with_links,
        sample_link,
        sample_path
    ):
        """Test adding tooltips to links in content."""
        paths = {"docs/target.md": sample_path}
        result = add_tooltips_to_links(
            sample_content_with_links,
            [sample_link],
            paths
        )
        
        # Check that tooltips are added
        assert 'class="nova-link-wrapper"' in result
        assert 'data-tooltip="' in result
        
        # Check that original links are preserved
        assert "[Target Doc](docs/target.md#section-1)" in result
        assert "[Related](docs/related.md)" in result
        
        # Check that tooltip content is included
        assert sample_link.context in result
        assert sample_link.title in result
    
    def test_add_tooltips_without_paths(
        self,
        sample_content_with_links,
        sample_link
    ):
        """Test adding tooltips without navigation paths."""
        result = add_tooltips_to_links(
            sample_content_with_links,
            [sample_link],
            None
        )
        
        # Check that tooltips are added without path information
        assert 'class="nova-link-wrapper"' in result
        assert 'data-tooltip="' in result
        assert sample_link.context in result
        
        # Original content should be preserved
        assert "[Target Doc](docs/target.md#section-1)" in result 