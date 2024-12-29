"""Unit tests for link model components."""

import pytest
from pathlib import Path
from datetime import datetime

from nova.models.links import LinkType, LinkContext
from nova.models.link_map import (
    NavigationPathType,
    NavigationNode,
    NavigationPath,
    LinkRepairStrategy,
    LinkRepairResult
)


class TestLinkType:
    """Tests for LinkType enumeration."""
    
    def test_link_type_values(self):
        """Test that LinkType has expected values."""
        assert LinkType.OUTGOING.value == "outgoing"
        assert LinkType.INCOMING.value == "incoming"
        assert LinkType.BIDIRECTIONAL.value == "bidirectional"
    
    def test_link_type_comparison(self):
        """Test that LinkType values can be compared."""
        assert LinkType.OUTGOING != LinkType.INCOMING
        assert LinkType.OUTGOING == LinkType.OUTGOING
        assert LinkType.BIDIRECTIONAL != LinkType.OUTGOING


class TestLinkContext:
    """Tests for LinkContext model."""
    
    @pytest.fixture
    def sample_link(self):
        """Create a sample link context."""
        return LinkContext(
            source_file="source.md",
            target_file="target.md",
            target_section="section-1",
            link_type=LinkType.OUTGOING,
            context="Sample context",
            title="Sample Link"
        )
    
    def test_link_context_creation(self, sample_link):
        """Test that LinkContext can be created with all fields."""
        assert sample_link.source_file == "source.md"
        assert sample_link.target_file == "target.md"
        assert sample_link.target_section == "section-1"
        assert sample_link.link_type == LinkType.OUTGOING
        assert sample_link.context == "Sample context"
        assert sample_link.title == "Sample Link"
    
    def test_link_context_defaults(self):
        """Test that LinkContext has appropriate defaults."""
        link = LinkContext(source_file="source.md", target_file="target.md")
        assert link.target_section is None
        assert link.link_type == LinkType.OUTGOING
        assert link.context is None
        assert link.title is None
    
    def test_link_context_validation(self):
        """Test that LinkContext validates required fields."""
        with pytest.raises(ValueError):
            LinkContext(source_file="", target_file="target.md")
        with pytest.raises(ValueError):
            LinkContext(source_file="source.md", target_file="")
    
    def test_link_context_equality(self, sample_link):
        """Test that LinkContext equality works correctly."""
        same_link = LinkContext(
            source_file="source.md",
            target_file="target.md",
            target_section="section-1",
            link_type=LinkType.OUTGOING,
            context="Sample context",
            title="Sample Link"
        )
        different_link = LinkContext(
            source_file="other.md",
            target_file="target.md"
        )
        assert sample_link == same_link
        assert sample_link != different_link


class TestNavigationNode:
    """Tests for NavigationNode model."""
    
    @pytest.fixture
    def sample_node(self):
        """Create a sample navigation node."""
        return NavigationNode(
            file_path="test.md",
            section_id="section-1",
            title="Test Section",
            context="Test context"
        )
    
    def test_navigation_node_creation(self, sample_node):
        """Test that NavigationNode can be created with all fields."""
        assert sample_node.file_path == "test.md"
        assert sample_node.section_id == "section-1"
        assert sample_node.title == "Test Section"
        assert sample_node.context == "Test context"
    
    def test_navigation_node_defaults(self):
        """Test that NavigationNode has appropriate defaults."""
        node = NavigationNode(file_path="test.md", section_id="section-1")
        assert node.title is None
        assert node.context is None


class TestNavigationPath:
    """Tests for NavigationPath model."""
    
    @pytest.fixture
    def sample_nodes(self):
        """Create sample navigation nodes."""
        return [
            NavigationNode(file_path="start.md", section_id="s1"),
            NavigationNode(file_path="middle.md", section_id="s2"),
            NavigationNode(file_path="end.md", section_id="s3")
        ]
    
    @pytest.fixture
    def sample_path(self, sample_nodes):
        """Create a sample navigation path."""
        return NavigationPath(
            path_type=NavigationPathType.INDIRECT,
            nodes=sample_nodes,
            total_links=2,
            bidirectional=False
        )
    
    def test_navigation_path_creation(self, sample_path, sample_nodes):
        """Test that NavigationPath can be created with all fields."""
        assert sample_path.path_type == NavigationPathType.INDIRECT
        assert sample_path.nodes == sample_nodes
        assert sample_path.total_links == 2
        assert not sample_path.bidirectional
        assert isinstance(sample_path.last_validated, datetime)
    
    def test_navigation_path_validation(self, sample_nodes):
        """Test that NavigationPath validates fields."""
        with pytest.raises(ValueError):
            NavigationPath(
                path_type=NavigationPathType.DIRECT,
                nodes=sample_nodes,  # Direct path should have 2 nodes
                total_links=2,
                bidirectional=False
            )
    
    def test_navigation_path_types(self, sample_nodes):
        """Test different navigation path types."""
        direct_path = NavigationPath(
            path_type=NavigationPathType.DIRECT,
            nodes=sample_nodes[:2],  # Only start and end
            total_links=1,
            bidirectional=False
        )
        assert direct_path.path_type == NavigationPathType.DIRECT
        assert len(direct_path.nodes) == 2
        
        bidirectional_path = NavigationPath(
            path_type=NavigationPathType.BIDIRECTIONAL,
            nodes=sample_nodes[:2],
            total_links=1,
            bidirectional=True
        )
        assert bidirectional_path.path_type == NavigationPathType.BIDIRECTIONAL
        assert bidirectional_path.bidirectional


class TestLinkRepairStrategy:
    """Tests for LinkRepairStrategy enumeration."""
    
    def test_repair_strategy_values(self):
        """Test that LinkRepairStrategy has expected values."""
        assert LinkRepairStrategy.FUZZY_MATCH.value == "fuzzy_match"
        assert LinkRepairStrategy.NEAREST_PATH.value == "nearest_path"
        assert LinkRepairStrategy.ALTERNATIVE_PATH.value == "alternative_path"
        assert LinkRepairStrategy.REMOVE_LINK.value == "remove_link"
    
    def test_repair_strategy_comparison(self):
        """Test that LinkRepairStrategy values can be compared."""
        assert LinkRepairStrategy.FUZZY_MATCH != LinkRepairStrategy.NEAREST_PATH
        assert LinkRepairStrategy.FUZZY_MATCH == LinkRepairStrategy.FUZZY_MATCH
        assert LinkRepairStrategy.REMOVE_LINK != LinkRepairStrategy.ALTERNATIVE_PATH


class TestLinkRepairResult:
    """Tests for LinkRepairResult model."""
    
    @pytest.fixture
    def sample_link(self):
        """Create a sample link context."""
        return LinkContext(
            source_file="source.md",
            target_file="old_target.md"
        )
    
    @pytest.fixture
    def sample_repair_result(self, sample_link):
        """Create a sample repair result."""
        return LinkRepairResult(
            original_link=sample_link,
            repaired_link=LinkContext(
                source_file="source.md",
                target_file="new_target.md"
            ),
            strategy_used=LinkRepairStrategy.FUZZY_MATCH,
            success=True,
            confidence=0.85,
            repair_notes="Found similar file"
        )
    
    def test_repair_result_creation(self, sample_repair_result, sample_link):
        """Test that LinkRepairResult can be created with all fields."""
        assert sample_repair_result.original_link == sample_link
        assert sample_repair_result.repaired_link is not None
        assert sample_repair_result.strategy_used == LinkRepairStrategy.FUZZY_MATCH
        assert sample_repair_result.success
        assert sample_repair_result.confidence == 0.85
        assert sample_repair_result.repair_notes == "Found similar file"
    
    def test_repair_result_defaults(self, sample_link):
        """Test that LinkRepairResult has appropriate defaults."""
        result = LinkRepairResult(original_link=sample_link)
        assert result.repaired_link is None
        assert result.strategy_used is None
        assert not result.success
        assert result.confidence == 0.0
        assert result.repair_notes == ""
    
    def test_repair_result_validation(self, sample_link):
        """Test that LinkRepairResult validates fields."""
        with pytest.raises(ValueError):
            LinkRepairResult(
                original_link=sample_link,
                confidence=-0.1  # Confidence should be between 0 and 1
            )
        with pytest.raises(ValueError):
            LinkRepairResult(
                original_link=sample_link,
                confidence=1.1  # Confidence should be between 0 and 1
            ) 