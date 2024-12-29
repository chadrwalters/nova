"""Link visualization components and utilities."""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import json
from pathlib import Path

from nova.models.links import LinkContext, LinkType
from nova.models.link_map import LinkRelationshipMap, NavigationPath


@dataclass
class VisualizationNode:
    """Node in the link visualization graph."""
    id: str
    label: str
    type: str
    metrics: Dict[str, int]
    status: str = "normal"  # normal, warning, error


@dataclass
class VisualizationEdge:
    """Edge in the link visualization graph."""
    source: str
    target: str
    type: LinkType
    bidirectional: bool = False
    status: str = "normal"  # normal, warning, error


class LinkVisualizer:
    """Generates link visualization components."""
    
    # JavaScript for interactive visualization
    VIS_SCRIPT = """
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
    function initLinkGraph(data, containerId) {
        const container = d3.select(`#${containerId}`);
        const width = container.node().getBoundingClientRect().width;
        const height = 600;
        
        // Create SVG
        const svg = container.append("svg")
            .attr("width", width)
            .attr("height", height);
            
        // Create force simulation
        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.edges).id(d => d.id))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));
            
        // Create arrow markers
        svg.append("defs").selectAll("marker")
            .data(["normal", "warning", "error", "bidirectional"])
            .enter().append("marker")
            .attr("id", d => `arrow-${d}`)
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 20)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("class", d => `arrow-${d}`);
            
        // Create edges
        const edges = svg.append("g")
            .selectAll("path")
            .data(data.edges)
            .enter().append("path")
            .attr("class", d => `edge edge-${d.status}${d.bidirectional ? " bidirectional" : ""}`)
            .attr("marker-end", d => `url(#arrow-${d.status})`);
            
        // Create nodes
        const nodes = svg.append("g")
            .selectAll("g")
            .data(data.nodes)
            .enter().append("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragStarted)
                .on("drag", dragged)
                .on("end", dragEnded));
                
        // Add node circles
        nodes.append("circle")
            .attr("r", 10)
            .attr("class", d => `node-${d.status}`);
            
        // Add node labels
        nodes.append("text")
            .attr("dy", -15)
            .text(d => d.label)
            .attr("class", "node-label");
            
        // Add node metrics
        nodes.append("text")
            .attr("dy", 20)
            .text(d => `${d.metrics.outgoing_links}↑ ${d.metrics.incoming_links}↓`)
            .attr("class", "node-metrics");
            
        // Update positions on tick
        simulation.on("tick", () => {
            edges.attr("d", d => {
                const dx = d.target.x - d.source.x;
                const dy = d.target.y - d.source.y;
                const dr = Math.sqrt(dx * dx + dy * dy);
                return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
            });
            
            nodes.attr("transform", d => `translate(${d.x},${d.y})`);
        });
        
        // Drag functions
        function dragStarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }
        
        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }
        
        function dragEnded(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }
    }
    </script>
    """
    
    # CSS styles for visualization
    VIS_STYLES = """
    /* Link Graph Styles */
    .nova-link-graph {
        margin: 2rem 0;
        border: 1px solid #e9ecef;
        border-radius: 0.5rem;
        overflow: hidden;
    }
    
    .nova-link-graph svg {
        background: #f8f9fa;
    }
    
    /* Node Styles */
    .node circle {
        stroke: #fff;
        stroke-width: 2px;
    }
    
    .node-normal {
        fill: #0d6efd;
    }
    
    .node-warning {
        fill: #ffc107;
    }
    
    .node-error {
        fill: #dc3545;
    }
    
    .node-label {
        font-size: 12px;
        text-anchor: middle;
        fill: #212529;
        pointer-events: none;
    }
    
    .node-metrics {
        font-size: 10px;
        text-anchor: middle;
        fill: #6c757d;
        pointer-events: none;
    }
    
    /* Edge Styles */
    .edge {
        fill: none;
        stroke-width: 2px;
    }
    
    .edge-normal {
        stroke: #6c757d;
    }
    
    .edge-warning {
        stroke: #ffc107;
    }
    
    .edge-error {
        stroke: #dc3545;
    }
    
    .edge.bidirectional {
        stroke-dasharray: 5,5;
    }
    
    /* Arrow Styles */
    .arrow-normal {
        fill: #6c757d;
    }
    
    .arrow-warning {
        fill: #ffc107;
    }
    
    .arrow-error {
        fill: #dc3545;
    }
    
    .arrow-bidirectional {
        fill: #6c757d;
    }
    
    /* Legend Styles */
    .nova-link-legend {
        margin-top: 1rem;
        padding: 1rem;
        background: white;
        border-top: 1px solid #e9ecef;
    }
    
    .nova-legend-item {
        display: inline-flex;
        align-items: center;
        margin-right: 1rem;
        font-size: 0.875rem;
    }
    
    .nova-legend-color {
        width: 12px;
        height: 12px;
        margin-right: 0.5rem;
        border-radius: 50%;
    }
    """
    
    def __init__(self, link_map: LinkRelationshipMap):
        """Initialize link visualizer.
        
        Args:
            link_map: Link relationship map to visualize
        """
        self.link_map = link_map
    
    def generate_graph_data(
        self,
        files: Set[str],
        include_warnings: bool = True
    ) -> Dict[str, List]:
        """Generate graph data for visualization.
        
        Args:
            files: Set of files to include in visualization
            include_warnings: Whether to include warning states
            
        Returns:
            Dictionary with nodes and edges lists
        """
        nodes = []
        edges = []
        
        # Create nodes
        for file in files:
            metrics = self.link_map.get_health_report(file)
            status = self._get_node_status(metrics, include_warnings)
            
            nodes.append(VisualizationNode(
                id=file,
                label=Path(file).stem,
                type="file",
                metrics=metrics,
                status=status
            ))
        
        # Create edges
        for source in files:
            related = self.link_map.get_related_files(source)
            
            # Add edges for outgoing links
            for target in related['outgoing']:
                if target in files:
                    edges.append(VisualizationEdge(
                        source=source,
                        target=target,
                        type=LinkType.OUTGOING,
                        bidirectional=target in related['bidirectional']
                    ))
        
        return {
            'nodes': [self._node_to_dict(n) for n in nodes],
            'edges': [self._edge_to_dict(e) for e in edges]
        }
    
    def render_graph(
        self,
        files: Set[str],
        container_id: str = "nova-link-graph",
        include_warnings: bool = True
    ) -> str:
        """Render an interactive link graph.
        
        Args:
            files: Set of files to include in visualization
            container_id: ID for the container element
            include_warnings: Whether to include warning states
            
        Returns:
            HTML string for the graph
        """
        # Generate graph data
        graph_data = self.generate_graph_data(files, include_warnings)
        
        # Create HTML
        html = [
            f'<div class="nova-link-graph" id="{container_id}">',
            self.VIS_SCRIPT,
            f'<style>{self.VIS_STYLES}</style>',
            '</div>',
            '<div class="nova-link-legend">',
            '  <div class="nova-legend-item">',
            '    <span class="nova-legend-color" style="background: #0d6efd"></span>',
            '    <span>Normal</span>',
            '  </div>',
            '  <div class="nova-legend-item">',
            '    <span class="nova-legend-color" style="background: #ffc107"></span>',
            '    <span>Warning</span>',
            '  </div>',
            '  <div class="nova-legend-item">',
            '    <span class="nova-legend-color" style="background: #dc3545"></span>',
            '    <span>Error</span>',
            '  </div>',
            '</div>',
            f'<script>initLinkGraph({json.dumps(graph_data)}, "{container_id}");</script>'
        ]
        
        return '\n'.join(html)
    
    def _get_node_status(self, metrics: Dict[str, int], include_warnings: bool) -> str:
        """Get status for a node based on its metrics.
        
        Args:
            metrics: Node metrics
            include_warnings: Whether to include warning states
            
        Returns:
            Status string
        """
        if metrics['broken_links'] > 0:
            return "error"
        if include_warnings and metrics['repair_attempts'] > metrics['repaired_links']:
            return "warning"
        return "normal"
    
    def _node_to_dict(self, node: VisualizationNode) -> Dict:
        """Convert node to dictionary for JSON serialization.
        
        Args:
            node: Node to convert
            
        Returns:
            Dictionary representation
        """
        return {
            'id': node.id,
            'label': node.label,
            'type': node.type,
            'metrics': node.metrics,
            'status': node.status
        }
    
    def _edge_to_dict(self, edge: VisualizationEdge) -> Dict:
        """Convert edge to dictionary for JSON serialization.
        
        Args:
            edge: Edge to convert
            
        Returns:
            Dictionary representation
        """
        return {
            'source': edge.source,
            'target': edge.target,
            'type': edge.type.value if edge.type else "link",
            'bidirectional': edge.bidirectional,
            'status': edge.status
        } 