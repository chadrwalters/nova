"""Link relationship mapping and navigation module."""

import difflib
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from .links import LinkContext, LinkType


class NavigationPathType(str, Enum):
    """Types of navigation paths between documents."""

    DIRECT = "direct"  # Direct link between documents
    INDIRECT = "indirect"  # Path through intermediate documents
    BIDIRECTIONAL = "bidirectional"  # Two-way link between documents


@dataclass
class NavigationNode:
    """Node in a navigation path."""

    file_path: str
    section_id: str
    title: Optional[str] = None
    context: Optional[str] = None


class NavigationPath(BaseModel):
    """Path between two documents through the link graph."""

    path_type: NavigationPathType = Field(description="Type of navigation path")
    nodes: List[NavigationNode] = Field(description="Nodes in the path")
    total_links: int = Field(description="Total number of links in the path")
    bidirectional: bool = Field(description="Whether the path is bidirectional")
    last_validated: datetime = Field(
        default_factory=datetime.now, description="When the path was last validated"
    )

    class Config:
        """Model configuration."""

        arbitrary_types_allowed = True


class LinkRepairStrategy(str, Enum):
    """Types of link repair strategies."""

    FUZZY_MATCH = "fuzzy_match"  # Try to find similar file/section names
    NEAREST_PATH = "nearest_path"  # Find nearest valid path in directory
    ALTERNATIVE_PATH = "alternative_path"  # Find alternative navigation path
    REMOVE_LINK = "remove_link"  # Remove broken link as last resort


class LinkRepairResult(BaseModel):
    """Result of a link repair attempt."""

    original_link: LinkContext
    repaired_link: Optional[LinkContext] = None
    strategy_used: Optional[LinkRepairStrategy] = None
    success: bool = False
    confidence: float = 0.0
    repair_notes: str = ""


class LinkRelationshipMap(BaseModel):
    """Map of relationships between documents based on links."""

    # Direct relationships (file -> directly linked files)
    direct_relationships: Dict[str, Set[str]] = Field(
        default_factory=lambda: defaultdict(set),
        description="Map of files to their directly linked files",
    )

    # Reverse relationships (file -> files that link to it)
    reverse_relationships: Dict[str, Set[str]] = Field(
        default_factory=lambda: defaultdict(set),
        description="Map of files to files that link to them",
    )

    # Navigation paths between files
    navigation_paths: Dict[Tuple[str, str], List[NavigationPath]] = Field(
        default_factory=dict, description="Map of file pairs to their navigation paths"
    )

    # Link health metrics
    health_metrics: Dict[str, Dict[str, int]] = Field(
        default_factory=lambda: defaultdict(
            lambda: {
                "total_links": 0,
                "valid_links": 0,
                "broken_links": 0,
                "incoming_links": 0,
                "outgoing_links": 0,
                "bidirectional_links": 0,
                "repaired_links": 0,
                "repair_attempts": 0,
            }
        ),
        description="Link health metrics for each file",
    )

    # Link repair history
    repair_history: Dict[str, List[LinkRepairResult]] = Field(
        default_factory=lambda: defaultdict(list),
        description="History of link repairs by file",
    )

    def add_link(self, link: LinkContext) -> None:
        """Add a link to the relationship map.

        Args:
            link: Link context to add
        """
        source = link.source_file
        target = link.target_file

        # Add direct relationship
        self.direct_relationships[source].add(target)

        # Add reverse relationship
        self.reverse_relationships[target].add(source)

        # Update health metrics
        self._update_health_metrics(source, target)

    def _update_health_metrics(self, source: str, target: str) -> None:
        """Update health metrics for a link.

        Args:
            source: Source file path
            target: Target file path
        """
        # Update source metrics
        self.health_metrics[source]["total_links"] += 1
        self.health_metrics[source]["outgoing_links"] += 1

        # Update target metrics
        self.health_metrics[target]["total_links"] += 1
        self.health_metrics[target]["incoming_links"] += 1

        # Check for bidirectional link
        if source in self.reverse_relationships[target]:
            self.health_metrics[source]["bidirectional_links"] += 1
            self.health_metrics[target]["bidirectional_links"] += 1

    def find_navigation_paths(
        self, source: str, target: str, max_depth: int = 3
    ) -> List[NavigationPath]:
        """Find all navigation paths between two files.

        Args:
            source: Source file path
            target: Target file path
            max_depth: Maximum path depth to search

        Returns:
            List of navigation paths
        """
        paths = []
        visited = set()

        def dfs(current: str, path: List[str], depth: int) -> None:
            """Depth-first search for paths."""
            if depth > max_depth:
                return

            if current == target:
                # Create navigation path
                nodes = [NavigationNode(file_path=file, section_id="") for file in path]
                path_type = (
                    NavigationPathType.DIRECT
                    if len(path) == 2
                    else NavigationPathType.INDIRECT
                )
                bidirectional = all(
                    next_file in self.direct_relationships[file]
                    for file, next_file in zip(path[:-1], path[1:])
                )

                paths.append(
                    NavigationPath(
                        path_type=path_type,
                        nodes=nodes,
                        total_links=len(path) - 1,
                        bidirectional=bidirectional,
                    )
                )
                return

            visited.add(current)
            for next_file in self.direct_relationships[current]:
                if next_file not in visited:
                    dfs(next_file, path + [next_file], depth + 1)
            visited.remove(current)

        # Start DFS from source
        dfs(source, [source], 0)

        # Cache the paths
        self.navigation_paths[(source, target)] = paths

        return paths

    def get_navigation_paths(
        self, source: str, target: str, max_depth: int = 3
    ) -> List[NavigationPath]:
        """Get navigation paths between two files.

        Args:
            source: Source file path
            target: Target file path
            max_depth: Maximum path depth to search

        Returns:
            List of navigation paths
        """
        # Check cache first
        if (source, target) in self.navigation_paths:
            return self.navigation_paths[(source, target)]

        # Find and cache paths
        return self.find_navigation_paths(source, target, max_depth)

    def get_health_report(self, file_path: str) -> Dict[str, int]:
        """Get health metrics for a file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary of health metrics
        """
        return self.health_metrics[file_path]

    def get_related_files(self, file_path: str) -> Dict[str, Set[str]]:
        """Get all files related to a file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with 'outgoing', 'incoming', and 'bidirectional' file sets
        """
        outgoing = self.direct_relationships[file_path]
        incoming = self.reverse_relationships[file_path]
        bidirectional = outgoing & incoming

        return {
            "outgoing": outgoing - bidirectional,
            "incoming": incoming - bidirectional,
            "bidirectional": bidirectional,
        }

    def get_link_suggestions(self, file_path: str) -> List[str]:
        """Get suggestions for new links.

        Args:
            file_path: Path to file

        Returns:
            List of suggested files to link to
        """
        suggestions = []

        # Get files that are linked to by files this file links to
        for target in self.direct_relationships[file_path]:
            suggestions.extend(self.direct_relationships[target])

        # Get files that link to files that link to this file
        for source in self.reverse_relationships[file_path]:
            suggestions.extend(self.reverse_relationships[source])

        # Remove duplicates and existing links
        suggestions = set(suggestions)
        suggestions -= {file_path}  # Remove self
        suggestions -= self.direct_relationships[file_path]  # Remove existing links

        return sorted(suggestions)

    def repair_link(
        self,
        link: LinkContext,
        available_files: Set[str],
        strategies: Optional[List[LinkRepairStrategy]] = None,
    ) -> LinkRepairResult:
        """Attempt to repair a broken link.

        Args:
            link: Broken link to repair
            available_files: Set of available file paths
            strategies: Optional list of repair strategies to try

        Returns:
            Result of repair attempt
        """
        if strategies is None:
            strategies = list(LinkRepairStrategy)

        result = LinkRepairResult(original_link=link)
        source_file = link.source_file

        # Update repair attempt metrics
        self.health_metrics[source_file]["repair_attempts"] += 1

        for strategy in strategies:
            if strategy == LinkRepairStrategy.FUZZY_MATCH:
                repaired = self._repair_fuzzy_match(link, available_files)
            elif strategy == LinkRepairStrategy.NEAREST_PATH:
                repaired = self._repair_nearest_path(link, available_files)
            elif strategy == LinkRepairStrategy.ALTERNATIVE_PATH:
                repaired = self._repair_alternative_path(link, available_files)
            else:  # REMOVE_LINK
                repaired = self._repair_remove_link(link)

            if repaired.success:
                # Update metrics for successful repair
                self.health_metrics[source_file]["repaired_links"] += 1

                # Store repair history
                self.repair_history[source_file].append(repaired)

                return repaired

        # No repair strategies worked
        result.repair_notes = "All repair strategies failed"
        self.repair_history[source_file].append(result)
        return result

    def _repair_fuzzy_match(
        self, link: LinkContext, available_files: Set[str]
    ) -> LinkRepairResult:
        """Try to repair link using fuzzy matching.

        Args:
            link: Broken link to repair
            available_files: Set of available file paths

        Returns:
            Result of repair attempt
        """
        result = LinkRepairResult(original_link=link)
        target = link.target_file

        # Find best matching file
        matches = difflib.get_close_matches(target, available_files, n=1, cutoff=0.6)
        if not matches:
            result.repair_notes = "No close matches found"
            return result

        best_match = matches[0]
        similarity = difflib.SequenceMatcher(None, target, best_match).ratio()

        # Create repaired link if match is good enough
        if similarity >= 0.8:
            repaired_link = LinkContext(
                source_file=link.source_file,
                target_file=best_match,
                target_section=link.target_section,
                link_type=link.link_type,
                context=link.context,
            )
            result.repaired_link = repaired_link
            result.strategy_used = LinkRepairStrategy.FUZZY_MATCH
            result.success = True
            result.confidence = similarity
            result.repair_notes = f"Found similar file: {best_match}"
        else:
            result.repair_notes = (
                f"Best match {best_match} not confident enough ({similarity:.2f})"
            )

        return result

    def _repair_nearest_path(
        self, link: LinkContext, available_files: Set[str]
    ) -> LinkRepairResult:
        """Try to repair link by finding nearest valid path.

        Args:
            link: Broken link to repair
            available_files: Set of available file paths

        Returns:
            Result of repair attempt
        """
        result = LinkRepairResult(original_link=link)
        target = Path(link.target_file)

        # Try to find file with same name in different directory
        matches = [f for f in available_files if Path(f).name == target.name]
        if not matches:
            result.repair_notes = "No files with same name found"
            return result

        # Find closest path by directory similarity
        best_match = None
        best_similarity = 0
        for match in matches:
            match_path = Path(match)
            similarity = difflib.SequenceMatcher(
                None, str(target.parent), str(match_path.parent)
            ).ratio()
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = match

        if best_match and best_similarity >= 0.5:
            repaired_link = LinkContext(
                source_file=link.source_file,
                target_file=best_match,
                target_section=link.target_section,
                link_type=link.link_type,
                context=link.context,
            )
            result.repaired_link = repaired_link
            result.strategy_used = LinkRepairStrategy.NEAREST_PATH
            result.success = True
            result.confidence = best_similarity
            result.repair_notes = f"Found file in different directory: {best_match}"
        else:
            result.repair_notes = "No suitable path matches found"

        return result

    def _repair_alternative_path(
        self, link: LinkContext, available_files: Set[str]
    ) -> LinkRepairResult:
        """Try to repair link by finding alternative navigation path.

        Args:
            link: Broken link to repair
            available_files: Set of available file paths

        Returns:
            Result of repair attempt
        """
        result = LinkRepairResult(original_link=link)
        source = link.source_file

        # Look for alternative paths through the link graph
        for target in available_files:
            paths = self.get_navigation_paths(source, target)
            if paths:
                # Use shortest alternative path
                shortest = min(paths, key=lambda p: p.total_links)
                if shortest.total_links <= 2:  # Only use short paths
                    repaired_link = LinkContext(
                        source_file=source,
                        target_file=target,
                        target_section=link.target_section,
                        link_type=link.link_type,
                        context=f"Alternative path: {' -> '.join(n.file_path for n in shortest.nodes)}",
                    )
                    result.repaired_link = repaired_link
                    result.strategy_used = LinkRepairStrategy.ALTERNATIVE_PATH
                    result.success = True
                    result.confidence = 1.0 / shortest.total_links
                    result.repair_notes = (
                        f"Found alternative path through {shortest.total_links} links"
                    )
                    return result

        result.repair_notes = "No suitable alternative paths found"
        return result

    def _repair_remove_link(self, link: LinkContext) -> LinkRepairResult:
        """Remove broken link as last resort.

        Args:
            link: Broken link to remove

        Returns:
            Result of repair attempt
        """
        result = LinkRepairResult(original_link=link)
        result.strategy_used = LinkRepairStrategy.REMOVE_LINK
        result.success = True
        result.confidence = 1.0
        result.repair_notes = "Link removed as last resort"
        return result

    def get_repair_history(self, file_path: str) -> List[LinkRepairResult]:
        """Get repair history for a file.

        Args:
            file_path: Path to file

        Returns:
            List of repair results
        """
        return self.repair_history[file_path]

    def get_repair_suggestions(
        self, link: LinkContext, available_files: Set[str]
    ) -> List[Tuple[str, float]]:
        """Get repair suggestions for a broken link.

        Args:
            link: Broken link to get suggestions for
            available_files: Set of available file paths

        Returns:
            List of (suggested_file, confidence) tuples
        """
        suggestions = []

        # Try fuzzy matching
        fuzzy_result = self._repair_fuzzy_match(link, available_files)
        if fuzzy_result.repaired_link:
            suggestions.append(
                (fuzzy_result.repaired_link.target_file, fuzzy_result.confidence)
            )

        # Try nearest path
        path_result = self._repair_nearest_path(link, available_files)
        if path_result.repaired_link:
            suggestions.append(
                (path_result.repaired_link.target_file, path_result.confidence)
            )

        # Try alternative paths
        alt_result = self._repair_alternative_path(link, available_files)
        if alt_result.repaired_link:
            suggestions.append(
                (alt_result.repaired_link.target_file, alt_result.confidence)
            )

        # Sort by confidence and return top suggestions
        return sorted(suggestions, key=lambda x: x[1], reverse=True)
