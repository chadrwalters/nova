# mypy: disable-error-code="var-annotated"

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, TypedDict, cast

import networkx as nx  # type: ignore
import structlog
from networkx.algorithms.cycles import simple_cycles  # type: ignore
from networkx.algorithms.dag import ancestors, descendants  # type: ignore
from networkx.algorithms.shortest_paths.generic import shortest_path  # type: ignore
from networkx.classes.digraph import DiGraph
from networkx.exception import NetworkXNoPath

logger = structlog.get_logger(__name__)


@dataclass
class DocumentReference:
    """Reference between documents."""

    source_doc: Path
    target_doc: Path
    ref_type: str  # link, embed, attachment, etc.
    line_number: int
    context: str
    is_valid: bool
    error: Optional[str]


@dataclass
class DocumentDependency:
    """Dependency between documents."""

    source_doc: Path
    target_doc: Path
    dep_type: str  # requires, includes, references, etc.
    is_circular: bool
    path: List[Path]  # Path of dependencies if circular


@dataclass
class DocumentRelationships:
    """Collection of document relationships."""

    references: List[DocumentReference]
    dependencies: List[DocumentDependency]
    cycles: List[List[Path]]
    warnings: List[str]


class EdgeData(TypedDict):
    """Type definition for edge data in the graph."""

    ref_type: str
    line_number: int


@dataclass
class DocumentRelationshipManager:
    """Manages and analyzes relationships between documents."""

    base_dir: Path
    graph: DiGraph = field(default_factory=lambda: nx.DiGraph())  # type: ignore
    references: Dict[str, DocumentReference] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    type_counts: Dict[str, int] = field(default_factory=dict)  # type: ignore

    def __post_init__(self) -> None:
        """Initialize after dataclass initialization."""
        self.type_counts = {}

    def add_reference(
        self,
        source_doc: Path,
        target_doc: Path,
        ref_type: str,
        line_number: int,
        context: str,
    ) -> None:
        """Add a reference between documents."""
        try:
            # Normalize paths
            source_path = self._normalize_path(source_doc)
            target_path = self._normalize_path(target_doc)

            # Create reference key
            ref_key = f"{source_path}:{target_path}:{line_number}"

            # Validate reference
            is_valid, error = self._validate_reference(source_path, target_path)

            # Store reference
            self.references[ref_key] = DocumentReference(
                source_doc=source_path,
                target_doc=target_path,
                ref_type=ref_type,
                line_number=line_number,
                context=context,
                is_valid=is_valid,
                error=error,
            )

            # Update graph
            if is_valid:
                edge_data: EdgeData = {
                    "ref_type": ref_type,
                    "line_number": line_number,
                }
                self.graph.add_edge(
                    str(source_path),
                    str(target_path),
                    **edge_data,
                )

        except Exception as e:
            logger.error(
                "Failed to add reference",
                error=str(e),
                source=str(source_doc),
                target=str(target_doc),
            )
            self.warnings.append(
                f"Failed to add reference from {source_doc} to {target_doc}: {str(e)}"
            )

    def analyze_relationships(self) -> DocumentRelationships:
        """Analyze document relationships and detect issues."""
        try:
            # Find cycles in the dependency graph
            cycles_list = list(simple_cycles(self.graph))

            # Convert cycles to Path objects
            path_cycles = [[Path(node) for node in cycle] for cycle in cycles_list]

            # Get all dependencies
            dependencies = []
            for source, target, data in cast(
                List[Tuple[str, str, EdgeData]], self.graph.edges(data=True)
            ):
                # Check if this edge is part of a cycle
                is_circular = any(
                    source in cycle and target in cycle for cycle in cycles_list
                )

                # Find dependency path
                if is_circular:
                    path = shortest_path(self.graph, source=target, target=source)
                else:
                    path = []

                dependencies.append(
                    DocumentDependency(
                        source_doc=Path(source),
                        target_doc=Path(target),
                        dep_type=data["ref_type"],
                        is_circular=is_circular,
                        path=[Path(p) for p in path],
                    )
                )

            return DocumentRelationships(
                references=list(self.references.values()),
                dependencies=dependencies,
                cycles=path_cycles,
                warnings=self.warnings,
            )

        except Exception as e:
            logger.error("Failed to analyze relationships", error=str(e))
            return DocumentRelationships(
                references=[],
                dependencies=[],
                cycles=[],
                warnings=[f"Analysis failed: {str(e)}"],
            )

    def get_document_dependencies(self, doc_path: Path) -> List[Path]:
        """Get all documents that the given document depends on."""
        try:
            source = str(self._normalize_path(doc_path))
            if source in self.graph:
                # Get all reachable nodes
                reachable = descendants(self.graph, source)
                return [Path(node) for node in reachable]
            return []

        except Exception as e:
            logger.error(
                "Failed to get dependencies", error=str(e), document=str(doc_path)
            )
            return []

    def get_dependent_documents(self, doc_path: Path) -> List[Path]:
        """Get all documents that depend on the given document."""
        try:
            target = str(self._normalize_path(doc_path))
            if target in self.graph:
                # Get all predecessor nodes
                predecessors = ancestors(self.graph, target)
                return [Path(node) for node in predecessors]
            return []

        except Exception as e:
            logger.error(
                "Failed to get dependent documents",
                error=str(e),
                document=str(doc_path),
            )
            return []

    def check_circular_dependencies(self, doc_path: Path) -> List[List[Path]]:
        """Check for circular dependencies involving the given document."""
        try:
            source = str(self._normalize_path(doc_path))
            if source not in self.graph:
                return []

            # Find all cycles containing this node
            cycles_list = list(simple_cycles(self.graph))
            result_cycles = []
            for cycle in cycles_list:
                if source in cycle:
                    result_cycles.append([Path(node) for node in cycle])

            return result_cycles

        except Exception as e:
            logger.error(
                "Failed to check circular dependencies",
                error=str(e),
                document=str(doc_path),
            )
            return []

    def get_reference_chain(self, source_doc: Path, target_doc: Path) -> List[Path]:
        """Get the chain of references from source to target document."""
        try:
            source = str(self._normalize_path(source_doc))
            target = str(self._normalize_path(target_doc))

            if source in self.graph and target in self.graph:
                try:
                    # Find shortest path
                    path = shortest_path(self.graph, source=source, target=target)
                    return [Path(node) for node in path]
                except NetworkXNoPath:
                    return []
            return []

        except Exception as e:
            logger.error(
                "Failed to get reference chain",
                error=str(e),
                source=str(source_doc),
                target=str(target_doc),
            )
            return []

    def _normalize_path(self, path: Path) -> Path:
        """Normalize path relative to base directory."""
        try:
            if path.is_absolute():
                return path.relative_to(self.base_dir)
            return path

        except Exception:
            return path

    def _validate_reference(
        self, source_path: Path, target_path: Path
    ) -> tuple[bool, Optional[str]]:
        """Validate a document reference."""
        try:
            # Check if target exists
            full_target = self.base_dir / target_path
            if not full_target.exists():
                return False, "Target document does not exist"

            # Check if target is a file
            if not full_target.is_file():
                return False, "Target is not a file"

            # Check if target is a supported file type
            if not target_path.suffix.lower() in [".md", ".markdown"]:
                return False, "Target is not a markdown file"

            # Check for self-reference
            if source_path == target_path:
                return False, "Self-reference detected"

            return True, None

        except Exception as e:
            return False, str(e)

    def export_graph(self, output_file: Path) -> None:
        """Export the relationship graph to a DOT file."""
        try:
            # Add graph attributes
            for node in self.graph.nodes():
                self.graph.nodes[node]["label"] = Path(node).name

            for edge in self.graph.edges():
                data = self.graph.get_edge_data(*edge)
                self.graph.edges[edge]["label"] = data.get("ref_type", "")

            # Write DOT file
            nx.drawing.nx_pydot.write_dot(self.graph, output_file)  # type: ignore

        except Exception as e:
            logger.error("Failed to export graph", error=str(e), file=str(output_file))

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about document relationships."""
        try:
            stats = {
                "total_documents": self.graph.number_of_nodes(),
                "total_references": self.graph.number_of_edges(),
                "invalid_references": len(
                    [ref for ref in self.references.values() if not ref.is_valid]
                ),
                "circular_dependencies": len(list(simple_cycles(self.graph))),
                "reference_types": self._count_reference_types(),
            }

            return stats

        except Exception as e:
            logger.error("Failed to get statistics", error=str(e))
            return {}

    def _count_reference_types(self) -> Dict[str, int]:
        """Count occurrences of each reference type."""
        type_counts = {}
        for ref in self.references.values():
            ref_type = ref.ref_type
            type_counts[ref_type] = type_counts.get(ref_type, 0) + 1
        return type_counts


__all__ = [
    "DocumentRelationshipManager",
    "DocumentRelationships",
    "DocumentReference",
    "DocumentDependency",
]
