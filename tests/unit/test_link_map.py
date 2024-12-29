"""Unit tests for link map functionality."""

import pytest
from pathlib import Path

from nova.models.links import LinkType, LinkContext
from nova.models.link_map import (
    LinkRelationshipMap,
    NavigationPathType,
    NavigationNode,
    NavigationPath,
    LinkRepairStrategy,
    LinkRepairResult
)


@pytest.fixture
def sample_links():
    """Create a set of sample links for testing."""
    return [
        LinkContext(
            source_file="doc1.md",
            target_file="doc2.md",
            target_section="section1",
            link_type=LinkType.OUTGOING
        ),
        LinkContext(
            source_file="doc2.md",
            target_file="doc3.md",
            target_section="section2",
            link_type=LinkType.OUTGOING
        ),
        LinkContext(
            source_file="doc3.md",
            target_file="doc1.md",
            target_section="section3",
            link_type=LinkType.OUTGOING
        )
    ]


@pytest.fixture
def populated_map(sample_links):
    """Create a populated link map for testing."""
    link_map = LinkRelationshipMap()
    for link in sample_links:
        link_map.add_link(link)
    return link_map


class TestLinkRelationshipMap:
    """Tests for LinkRelationshipMap."""
    
    def test_add_link(self, populated_map):
        """Test adding links to the map."""
        # Check direct relationships
        assert "doc2.md" in populated_map.direct_relationships["doc1.md"]
        assert "doc3.md" in populated_map.direct_relationships["doc2.md"]
        assert "doc1.md" in populated_map.direct_relationships["doc3.md"]
        
        # Check reverse relationships
        assert "doc3.md" in populated_map.reverse_relationships["doc1.md"]
        assert "doc1.md" in populated_map.reverse_relationships["doc2.md"]
        assert "doc2.md" in populated_map.reverse_relationships["doc3.md"]
    
    def test_get_health_report(self, populated_map):
        """Test getting health metrics for a file."""
        health = populated_map.get_health_report("doc1.md")
        assert health['total_links'] == 2  # One outgoing, one incoming
        assert health['outgoing_links'] == 1
        assert health['incoming_links'] == 1
        assert health['bidirectional_links'] == 0  # No bidirectional links yet
    
    def test_get_related_files(self, populated_map):
        """Test getting related files."""
        related = populated_map.get_related_files("doc1.md")
        assert "doc2.md" in related['outgoing']
        assert "doc3.md" in related['incoming']
        assert not related['bidirectional']  # No bidirectional links yet
    
    def test_find_navigation_paths(self, populated_map):
        """Test finding navigation paths between files."""
        paths = populated_map.find_navigation_paths("doc1.md", "doc3.md")
        assert len(paths) == 2  # Should find both direct and indirect paths
        
        # Check direct path
        direct_path = next(p for p in paths if p.path_type == NavigationPathType.DIRECT)
        assert len(direct_path.nodes) == 2
        assert direct_path.nodes[0].file_path == "doc1.md"
        assert direct_path.nodes[1].file_path == "doc3.md"
        
        # Check indirect path
        indirect_path = next(p for p in paths if p.path_type == NavigationPathType.INDIRECT)
        assert len(indirect_path.nodes) == 3
        assert [n.file_path for n in indirect_path.nodes] == ["doc1.md", "doc2.md", "doc3.md"]
    
    def test_get_navigation_paths_caching(self, populated_map):
        """Test that navigation paths are cached."""
        # First call should compute paths
        paths1 = populated_map.get_navigation_paths("doc1.md", "doc3.md")
        
        # Second call should use cache
        paths2 = populated_map.get_navigation_paths("doc1.md", "doc3.md")
        
        assert paths1 == paths2
        assert ("doc1.md", "doc3.md") in populated_map.navigation_paths
    
    def test_get_link_suggestions(self, populated_map):
        """Test getting link suggestions."""
        suggestions = populated_map.get_link_suggestions("doc1.md")
        assert "doc3.md" in suggestions  # Should suggest doc3 through doc2
        
        # Should not suggest existing links or self
        assert "doc2.md" not in suggestions  # Already linked
        assert "doc1.md" not in suggestions  # Self link


class TestLinkRepair:
    """Tests for link repair functionality."""
    
    @pytest.fixture
    def available_files(self):
        """Create a set of available files for testing."""
        return {
            "documents/notes/doc1.md",
            "documents/notes/doc2.md",
            "documents/archive/old_doc.md",
            "documents/similar_doc.md"
        }
    
    @pytest.fixture
    def broken_link(self):
        """Create a broken link for testing repairs."""
        return LinkContext(
            source_file="documents/notes/doc1.md",
            target_file="documents/missing_doc.md",
            target_section="section1"
        )
    
    def test_fuzzy_match_repair(self, populated_map, broken_link, available_files):
        """Test fuzzy matching repair strategy."""
        result = populated_map._repair_fuzzy_match(broken_link, available_files)
        assert result.success
        assert result.strategy_used == LinkRepairStrategy.FUZZY_MATCH
        assert result.repaired_link.target_file == "documents/similar_doc.md"
        assert result.confidence >= 0.8
    
    def test_nearest_path_repair(self, populated_map, broken_link, available_files):
        """Test nearest path repair strategy."""
        result = populated_map._repair_nearest_path(broken_link, available_files)
        assert result.success
        assert result.strategy_used == LinkRepairStrategy.NEAREST_PATH
        assert result.repaired_link.target_file.startswith("documents/")
        assert result.confidence >= 0.5
    
    def test_alternative_path_repair(self, populated_map, broken_link, available_files):
        """Test alternative path repair strategy."""
        result = populated_map._repair_alternative_path(broken_link, available_files)
        if result.success:
            assert result.strategy_used == LinkRepairStrategy.ALTERNATIVE_PATH
            assert result.repaired_link is not None
            assert result.confidence > 0
    
    def test_remove_link_repair(self, populated_map, broken_link):
        """Test remove link repair strategy."""
        result = populated_map._repair_remove_link(broken_link)
        assert result.success
        assert result.strategy_used == LinkRepairStrategy.REMOVE_LINK
        assert result.repaired_link is None
        assert result.confidence == 1.0
    
    def test_repair_link_strategy_order(self, populated_map, broken_link, available_files):
        """Test that repair strategies are tried in order."""
        strategies = [
            LinkRepairStrategy.NEAREST_PATH,
            LinkRepairStrategy.REMOVE_LINK
        ]
        
        result = populated_map.repair_link(broken_link, available_files, strategies)
        assert result.success
        assert result.strategy_used == strategies[0]  # Should use first successful strategy
    
    def test_get_repair_suggestions(self, populated_map, broken_link, available_files):
        """Test getting repair suggestions."""
        suggestions = populated_map.get_repair_suggestions(broken_link, available_files)
        assert len(suggestions) > 0
        for target, confidence in suggestions:
            assert target in available_files
            assert 0 <= confidence <= 1


class TestMetrics:
    """Tests for link map metrics."""
    
    def test_health_metrics_update(self, populated_map, sample_links):
        """Test that health metrics are updated correctly."""
        # Add a bidirectional link
        reverse_link = LinkContext(
            source_file=sample_links[0].target_file,
            target_file=sample_links[0].source_file,
            link_type=LinkType.OUTGOING
        )
        populated_map.add_link(reverse_link)
        
        health = populated_map.get_health_report(sample_links[0].source_file)
        assert health['bidirectional_links'] == 1
        assert health['total_links'] == 2
    
    def test_repair_metrics(self, populated_map, broken_link, available_files):
        """Test that repair metrics are tracked correctly."""
        # Attempt repairs
        populated_map.repair_link(broken_link, available_files)
        
        health = populated_map.get_health_report(broken_link.source_file)
        assert health['repair_attempts'] == 1
        assert health['repaired_links'] >= 0  # Might be 0 if repair failed
    
    def test_repair_history(self, populated_map, broken_link, available_files):
        """Test that repair history is maintained."""
        populated_map.repair_link(broken_link, available_files)
        
        history = populated_map.get_repair_history(broken_link.source_file)
        assert len(history) == 1
        assert history[0].original_link == broken_link 