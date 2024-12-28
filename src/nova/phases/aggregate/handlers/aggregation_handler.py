#!/usr/bin/env python3
"""Handler for aggregating classified markdown content."""

# Standard library imports
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Nova package imports
from nova.models.parsed_result import ParsedResult


class AggregationHandler:
    """Handles the aggregation of classified markdown content."""
    
    def __init__(self, logger):
        self.logger = logger
    
    def load_classifications(self, input_dir: Path) -> List[ParsedResult]:
        """Load all classifications from a directory."""
        classifications = []
        
        try:
            # Find all JSON metadata files
            metadata_files = list(input_dir.glob('**/*.json'))
            self.logger.info(f"Found {len(metadata_files)} metadata files")
            
            for metadata_path in metadata_files:
                try:
                    # Load metadata
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Create ParsedResult from metadata
                    parsed_result = ParsedResult.from_dict(data)
                    classifications.append(parsed_result)
                    
                except Exception as e:
                    self.logger.error(f"Error loading {metadata_path}: {str(e)}")
                    continue
            
            return classifications
        
        except Exception as e:
            self.logger.error(f"Error loading classifications: {str(e)}")
            return []
    
    def aggregate_classifications(self, classifications: List[ParsedResult]) -> ParsedResult:
        """Aggregate multiple ParsedResult instances into one."""
        if not classifications:
            return ParsedResult()
        
        # Sort classifications by source file for consistent ordering
        sorted_classifications = sorted(classifications, key=lambda x: x.source_file)
        
        # Start with an empty result
        aggregated = ParsedResult(
            source_file="aggregated.md",
            metadata={
                'source_files': [c.source_file for c in sorted_classifications],
                'aggregation_info': {
                    'total_files': len(sorted_classifications),
                    'summary_sections': 0,
                    'raw_note_sections': 0,
                    'attachment_count': 0
                }
            }
        )
        
        # Add file markers and merge content
        for classification in sorted_classifications:
            # Add source file marker
            file_marker = f"\n\n## Source: {classification.source_file}\n\n"
            
            # Add summaries with marker
            if classification.summary_blocks:
                aggregated.summary_blocks.extend([
                    f"{file_marker}### Summary\n\n" + "\n\n".join(classification.summary_blocks)
                ])
                aggregated.metadata['aggregation_info']['summary_sections'] += 1
            
            # Add raw notes with marker
            if classification.raw_notes:
                aggregated.raw_notes.extend([
                    f"{file_marker}### Notes\n\n" + "\n\n".join(classification.raw_notes)
                ])
                aggregated.metadata['aggregation_info']['raw_note_sections'] += 1
            
            # Add attachments with marker
            if classification.attachments:
                aggregated.attachments.extend([
                    f"{file_marker}### Attachments\n\n" + "\n\n".join(classification.attachments)
                ])
                aggregated.metadata['aggregation_info']['attachment_count'] += len(classification.attachments)
            
            # Add to combined markdown
            aggregated.combined_markdown += (
                f"{file_marker}"
                f"{classification.combined_markdown}\n\n"
                f"{'=' * 80}\n\n"  # Add separator
            )
        
        return aggregated
    
    def save_aggregated_result(self, output_dir: Path, result: ParsedResult):
        """Save the aggregated classification data."""
        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Base paths for output files
            base_path = output_dir / "aggregated"
            
            # Save summary blocks
            if result.summary_blocks:
                summary_path = base_path.with_name("aggregated_summary.md")
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write("\n\n".join(result.summary_blocks))
            
            # Save raw notes
            if result.raw_notes:
                notes_path = base_path.with_name("aggregated_raw_notes.md")
                with open(notes_path, 'w', encoding='utf-8') as f:
                    f.write("\n\n".join(result.raw_notes))
            
            # Save attachments
            if result.attachments:
                attachments_path = base_path.with_name("aggregated_attachments.md")
                with open(attachments_path, 'w', encoding='utf-8') as f:
                    f.write("\n\n".join(result.attachments))
            
            # Save combined markdown
            combined_path = base_path.with_name("aggregated.md")
            with open(combined_path, 'w', encoding='utf-8') as f:
                f.write(result.combined_markdown)
            
            # Save metadata
            metadata_path = base_path.with_suffix('.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2)
            
            self.logger.info(f"Saved aggregated files in: {output_dir}")
        
        except Exception as e:
            self.logger.error(f"Error saving aggregated files: {str(e)}")
    
    def create_table_of_contents(self, result: ParsedResult) -> str:
        """Create a table of contents for the aggregated content."""
        toc = ["# Table of Contents\n"]
        
        # Add summaries section if exists
        if result.summary_blocks:
            toc.append("\n## Summaries\n")
            for source in result.metadata.get('source_files', []):
                toc.append(f"- Summary from {source}")
        
        # Add notes section if exists
        if result.raw_notes:
            toc.append("\n## Raw Notes\n")
            for source in result.metadata.get('source_files', []):
                toc.append(f"- Notes from {source}")
        
        # Add attachments section if exists
        if result.attachments:
            toc.append("\n## Attachments\n")
            for source in result.metadata.get('source_files', []):
                toc.append(f"- Attachments from {source}")
        
        # Add statistics
        info = result.metadata.get('aggregation_info', {})
        toc.append("\n## Statistics\n")
        toc.append(f"- Total Files: {info.get('total_files', 0)}")
        toc.append(f"- Summary Sections: {info.get('summary_sections', 0)}")
        toc.append(f"- Raw Note Sections: {info.get('raw_note_sections', 0)}")
        toc.append(f"- Total Attachments: {info.get('attachment_count', 0)}")
        
        return "\n".join(toc) 