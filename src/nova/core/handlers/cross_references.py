"""Cross-reference management for the Nova document processor."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from nova.core.config import NovaConfig
from nova.core.errors import ProcessingError


@dataclass
class Reference:
    """A reference between documents."""
    source: str
    target: str
    text: str
    is_metadata: bool = False


class CrossReferenceManager:
    """Manages cross-references between documents."""

    def __init__(self, config: NovaConfig):
        """Initialize the cross-reference manager.
        
        Args:
            config: The Nova configuration.
        """
        self.config = config
        self._references: Dict[str, List[Reference]] = {}
        self._reverse_refs: Dict[str, List[Reference]] = {}

    def add_reference(self, source: str, target: str, text: str, is_metadata: bool = False) -> None:
        """Add a reference between documents."""
        # Normalize paths for case-insensitive comparison
        source = str(Path(source))
        target = str(Path(target))
        
        # Create reference object
        ref = Reference(source=source, target=target, text=text, is_metadata=is_metadata)
        
        # Check for duplicates using normalized paths
        if source not in self._references:
            self._references[source] = []
        
        # Only add if not a duplicate (case-insensitive comparison)
        if not any(r.target.lower() == target.lower() and r.text == text for r in self._references[source]):
            self._references[source].append(ref)

    def get_references(self, source: str, include_metadata: bool = False) -> List[Reference]:
        """Get all references from a document.
        
        Args:
            source: The source document path.
            include_metadata: Whether to include metadata references.
            
        Returns:
            A list of references from the document.
        """
        if source not in self._references:
            return []
        
        refs = self._references[source]
        if not include_metadata:
            refs = [ref for ref in refs if not ref.is_metadata]
        return refs

    def get_reverse_references(self, target: str) -> List[Reference]:
        """Get all references to a document.
        
        Args:
            target: The target document path.
            
        Returns:
            A list of references to the document.
        """
        return self._reverse_refs.get(target, [])

    def validate_references(self) -> List[str]:
        """Validate all references."""
        errors = []
        visited: Set[str] = set()
        
        def check_circular(source: str, path: List[str]) -> None:
            """Check for circular references."""
            if source in path:
                cycle = " -> ".join(path[path.index(source):] + [source])
                errors.append(f"Circular reference detected: {cycle}")
                return
            
            path.append(source)
            for ref in self.get_references(source):
                check_circular(ref.target, path.copy())
        
        # Check for broken references
        for source, refs in self._references.items():
            for ref in refs:
                if not Path(ref.target).exists():
                    errors.append(f"Failed to resolve reference {ref.target}: Path does not exist")
        
        # Check for circular references
        for source in self._references:
            if source not in visited:
                check_circular(source, [])
                visited.add(source)
        
        return errors

    def get_validation_summary(self) -> str:
        """Get a summary of reference validation."""
        errors = self.validate_references()
        total_refs = sum(len(refs) for refs in self._references.values())
        broken_refs = len([e for e in errors if "Failed to resolve reference" in e])
        valid_refs = total_refs - broken_refs
        
        summary = [
            f"Total references: {total_refs}",
            f"Broken references: {broken_refs}",
            f"Valid references: {valid_refs}",
            "",
            "Errors:"
        ]
        
        if errors:
            summary.extend(f"- {error}" for error in errors)
        
        return "\n".join(summary) 