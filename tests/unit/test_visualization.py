"""Unit tests for visualization components."""

import pytest
import json
from pathlib import Path

from nova.models.links import LinkType, LinkContext
from nova.models.link_map import (
    LinkRelationshipMap,
    NavigationPath,
    NavigationNode
)
from nova.ui.visualization import (
    VisualizationNode,
    VisualizationEdge,
    LinkVisualizer
)


@pytest.fixture
def sample_files():
    """Create a set of sample files for testing."""
    return {
        "docs/main.md",
        "docs/section1.md",
        "docs/section2.md",
        "docs/section3.md"
    }


@pytest.fixture
def sample_links():
    """Create a set of sample links for testing."""
    return [
        LinkContext(
            source_file="docs/main.md",
            target_file="docs/section1.md",
            link_type=LinkType.OUTGOING
        ),
        LinkContext(
            source_file="docs/section1.md",
            target_file="docs/section2.md",
            link_type=LinkType.OUTGOING
        ),
        LinkContext(
            source_file="docs/section2.md",
            target_file="docs/section3.md",
            link_type=LinkType.OUTGOING
        ),
        LinkContext(
            source_file="docs/section3.md",
            target_file="docs/main.md",
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


@pytest.fixture
def visualizer(populated_map):
    """Create a link visualizer for testing."""
    return LinkVisualizer(populated_map)


class TestVisualizationNode:
    """Tests for VisualizationNode."""
    
    def test_node_creation(self):
        """Test that VisualizationNode can be created with all fields."""
        metrics = {
            'total_links': 2,
            'outgoing_links': 1,
            'incoming_links': 1
        }
        node = VisualizationNode(
            id="docs/test.md",
            label="test",
            type="file",
            metrics=metrics,
            status="normal"
        )
        
        assert node.id == "docs/test.md"
        assert node.label == "test"
        assert node.type == "file"
        assert node.metrics == metrics
        assert node.status == "normal"
    
    def test_node_defaults(self):
        """Test that VisualizationNode has appropriate defaults."""
        node = VisualizationNode(
            id="test.md",
            label="test",
            type="file",
            metrics={}
        )
        assert node.status == "normal"


class TestVisualizationEdge:
    """Tests for VisualizationEdge."""
    
    def test_edge_creation(self):
        """Test that VisualizationEdge can be created with all fields."""
        edge = VisualizationEdge(
            source="docs/source.md",
            target="docs/target.md",
            type=LinkType.OUTGOING,
            bidirectional=True,
            status="normal"
        )
        
        assert edge.source == "docs/source.md"
        assert edge.target == "docs/target.md"
        assert edge.type == LinkType.OUTGOING
        assert edge.bidirectional
        assert edge.status == "normal"
    
    def test_edge_defaults(self):
        """Test that VisualizationEdge has appropriate defaults."""
        edge = VisualizationEdge(
            source="source.md",
            target="target.md",
            type=LinkType.OUTGOING
        )
        assert not edge.bidirectional
        assert edge.status == "normal"


class TestLinkVisualizer:
    """Tests for LinkVisualizer."""
    
    def test_generate_graph_data(self, visualizer, sample_files):
        """Test generating graph data."""
        data = visualizer.generate_graph_data(sample_files)
        
        # Check structure
        assert 'nodes' in data
        assert 'edges' in data
        
        # Check nodes
        assert len(data['nodes']) == len(sample_files)
        for node in data['nodes']:
            assert node['id'] in sample_files
            assert 'metrics' in node
            assert 'status' in node
        
        # Check edges
        assert len(data['edges']) > 0
        for edge in data['edges']:
            assert edge['source'] in sample_files
            assert edge['target'] in sample_files
            assert 'type' in edge
            assert 'bidirectional' in edge
    
    def test_node_status_calculation(self, visualizer):
        """Test node status calculation."""
        # Test normal status
        metrics = {'broken_links': 0, 'repair_attempts': 0, 'repaired_links': 0}
        assert visualizer._get_node_status(metrics, True) == "normal"
        
        # Test warning status
        metrics = {'broken_links': 0, 'repair_attempts': 2, 'repaired_links': 1}
        assert visualizer._get_node_status(metrics, True) == "warning"
        
        # Test error status
        metrics = {'broken_links': 1, 'repair_attempts': 0, 'repaired_links': 0}
        assert visualizer._get_node_status(metrics, True) == "error"
    
    def test_render_graph(self, visualizer, sample_files):
        """Test rendering graph HTML."""
        html = visualizer.render_graph(sample_files)
        
        # Check basic structure
        assert '<div class="nova-link-graph"' in html
        assert '<script src="https://d3js.org/d3.v7.min.js"></script>' in html
        assert '<style>' in html
        
        # Check that graph data is included
        assert 'initLinkGraph(' in html
        
        # Check that legend is included
        assert '<div class="nova-link-legend">' in html
        assert 'Normal' in html
        assert 'Warning' in html
        assert 'Error' in html
    
    def test_graph_data_serialization(self, visualizer, sample_files):
        """Test that graph data can be serialized to JSON."""
        data = visualizer.generate_graph_data(sample_files)
        
        # Should not raise any errors
        json_str = json.dumps(data)
        
        # Should be able to parse back
        parsed = json.loads(json_str)
        assert parsed['nodes'] == data['nodes']
        assert parsed['edges'] == data['edges']
    
    def test_warning_state_handling(self, visualizer, sample_files):
        """Test handling of warning states in visualization."""
        # Test with warnings enabled
        data_with_warnings = visualizer.generate_graph_data(
            sample_files,
            include_warnings=True
        )
        
        # Test with warnings disabled
        data_without_warnings = visualizer.generate_graph_data(
            sample_files,
            include_warnings=False
        )
        
        # Should have different status distributions
        warning_count_with = len([
            n for n in data_with_warnings['nodes']
            if n['status'] == "warning"
        ])
        warning_count_without = len([
            n for n in data_without_warnings['nodes']
            if n['status'] == "warning"
        ])
        
        assert warning_count_with >= warning_count_without 