"""Consolidation handler for markdown files."""

# Standard library imports
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Third-party imports
from markitdown import MarkItDown
from rich.console import Console

# Nova package imports
from nova.core.models.result import ProcessingResult
from nova.core.pipeline import PipelineState
from nova.core.utils.metrics import MetricsTracker, MonitoringManager, TimingManager
from nova.phases.parse.handlers.base_markdown_handler import BaseMarkdownHandler


class ConsolidationHandler(BaseMarkdownHandler):
    """Handler for consolidating markdown files."""
    
    def __init__(self, config: Dict[str, Any], timing: TimingManager,
                 metrics: MetricsTracker, console: Console,
                 pipeline_state: PipelineState,
                 monitoring: Optional[MonitoringManager] = None) -> None:
        """Initialize the handler."""
        super().__init__(config, timing, metrics, console, pipeline_state, monitoring)
        
        # Initialize markdown parser
        self.parser = MarkItDown()
        
        # Initialize consolidation patterns
        self.consolidation_patterns = {
            'headers': r'^#{1,6}\s+.*$',
            'code_blocks': r'```[\s\S]*?```',
            'lists': r'^\s*[-*+]\s+.*$'
        }
        
        # Override with custom patterns if provided
        if 'consolidation' in config and 'patterns' in config['consolidation']:
            self.consolidation_patterns.update(config['consolidation']['patterns'])

    def _parse_sections(self, content: str) -> Dict[str, List[str]]:
        """Parse sections from markdown content."""
        sections: Dict[str, List[str]] = {name: [] for name in self.consolidation_patterns}
        lines = content.split('\n')
        
        for line in lines:
            for section_name, pattern in self.consolidation_patterns.items():
                if re.match(pattern, line, re.MULTILINE):
                    sections[section_name].append(line.strip())
                    
        return sections

    async def _process_impl(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing consolidated content
        """
        try:
            # Validate context and get output directory
            if not context or 'output_dir' not in context:
                error_msg = "No output directory specified in context"
                if self.monitoring:
                    self.monitoring.record_error(error_msg)
                return ProcessingResult(success=False, error=error_msg, errors=[error_msg])
                
            output_dir = Path(context['output_dir'])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Read and parse the markdown file
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Parse sections
            sections = self._parse_sections(content)
            
            # Create consolidated output
            consolidated = []
            for section_name, lines in sections.items():
                if lines:
                    consolidated.append(f"\n## {section_name.title()}\n")
                    consolidated.extend(lines)
                    
            consolidated_content = '\n'.join(consolidated)
            
            # Create output file
            output_file = output_dir / f"consolidated_{file_path.name}"
            with open(output_file, 'w') as f:
                f.write(consolidated_content)
                
            # Record metrics
            if self.monitoring:
                self.monitoring.record_metric('consolidated_size', len(consolidated_content))
                for section_name, lines in sections.items():
                    self.monitoring.record_metric(f'{section_name}_count', len(lines))
                    
            metadata = {
                'sections': sections,
                'output_file': str(output_file),
                'metrics': {
                    'consolidated_size': len(consolidated_content),
                    **{f'{name}_count': len(lines) for name, lines in sections.items()}
                }
            }
            
            return ProcessingResult(
                success=True,
                output=consolidated_content,
                content=str(output_file),
                metadata=metadata,
                output_files={output_file}
            )
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            if self.monitoring:
                self.monitoring.record_error(error_msg)
            return ProcessingResult(success=False, error=error_msg, errors=[error_msg])

    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a markdown file and consolidate its content.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context containing output_dir
            
        Returns:
            ProcessingResult containing the processing outcome
        """
        try:
            # Validate file
            if not self.can_handle(file_path):
                return ProcessingResult(
                    success=False,
                    error=f"Cannot handle file {file_path}",
                    errors=[f"Cannot handle file {file_path}"]
                )

            if not file_path.exists():
                return ProcessingResult(
                    success=False,
                    error=f"Input file does not exist: {file_path}",
                    errors=[f"Input file does not exist: {file_path}"]
                )
                
            # Validate context and get output directory
            if not context or 'output_dir' not in context:
                error_msg = "No output directory specified in context"
                if self.monitoring:
                    self.monitoring.record_error(error_msg)
                return ProcessingResult(success=False, error=error_msg, errors=[error_msg])
                
            output_dir = Path(context['output_dir'])
            output_dir.mkdir(parents=True, exist_ok=True)

            # Read and parse content
            content = file_path.read_text()
            sections = self._parse_sections(content)
            
            # Create output files
            output_files = set()
            
            # Create markdown output file
            md_output_file = output_dir / file_path.name
            md_output_file.write_text(content)
            output_files.add(md_output_file)
            
            # Create JSON output file
            json_output_file = output_dir / f"{file_path.stem}.json"
            json_output_file.write_text(str(sections))  # Simple string representation for now
            output_files.add(json_output_file)

            return ProcessingResult(
                success=True,
                output=str(md_output_file),
                content=content,
                metadata=sections,
                output_files=output_files
            )
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            if self.monitoring:
                self.monitoring.record_error(error_msg)
            return ProcessingResult(success=False, error=error_msg, errors=[error_msg])

    def validate_output(self, output_file: Path) -> bool:
        """Validate the output file.
        
        Args:
            output_file: Path to the output file to validate
            
        Returns:
            True if the output file is valid, False otherwise
        """
        if not output_file.exists():
            if self.monitoring:
                self.monitoring.record_error(f"Output file {output_file} does not exist")
            return False
            
        if not output_file.is_file():
            if self.monitoring:
                self.monitoring.record_error(f"Output path {output_file} is not a file")
            return False
            
        try:
            with open(output_file, 'r') as f:
                content = f.read()
                
            # Validate that the file contains at least one section
            sections = self._parse_sections(content)
            if not any(sections.values()):
                if self.monitoring:
                    self.monitoring.record_error(f"Output file {output_file} contains no sections")
                return False
                
            return True
            
        except Exception as e:
            if self.monitoring:
                self.monitoring.record_error(f"Error validating output file {output_file}: {str(e)}")
            return False 