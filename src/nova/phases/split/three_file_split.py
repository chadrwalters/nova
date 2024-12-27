"""Configuration and implementation for ThreeFileSplitProcessor."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from pydantic import ConfigDict, Field
from rich.console import Console
import json
from datetime import datetime

from ...core.config import ProcessorConfig, PipelineConfig
from ...core.pipeline.base import BaseProcessor
from ...core.utils.metrics import MetricsTracker
from ...core.utils.timing import TimingManager
from ...core.models.result import ProcessingResult

from .handlers.split import SplitHandler


class ThreeFileSplitConfig(ProcessorConfig):
    """Configuration for ThreeFileSplitProcessor."""
    
    enabled: bool = True
    processor: str = "ThreeFileSplitProcessor"
    output_dir: str = "output"
    options: Dict[str, Any] = Field(
        default_factory=lambda: {
            'components': {
                'three_file_split_processor': {
                    'config': {
                        'output_files': {
                            'summary': 'summary.md',
                            'raw_notes': 'raw_notes.md',
                            'attachments': 'attachments.md'
                        },
                        'section_markers': {
                            'summary': '--==SUMMARY==--',
                            'raw_notes': '--==RAW_NOTES==--',
                            'attachments': '--==ATTACHMENTS==--'
                        },
                        'attachment_markers': {
                            'start': '--==ATTACHMENT_BLOCK: {filename}==--',
                            'end': '--==ATTACHMENT_BLOCK_END==--'
                        },
                        'content_type_rules': {
                            'summary': [
                                'Contains high-level overviews',
                                'Contains key insights and decisions',
                                'Contains structured content'
                            ],
                            'raw_notes': [
                                'Contains detailed notes and logs',
                                'Contains chronological entries',
                                'Contains unstructured content'
                            ],
                            'attachments': [
                                'Contains file references',
                                'Contains embedded content',
                                'Contains metadata'
                            ]
                        },
                        'content_preservation': {
                            'validate_input_size': True,
                            'validate_output_size': True,
                            'track_content_markers': True,
                            'verify_section_integrity': True
                        },
                        'cross_linking': True,
                        'preserve_headers': True
                    }
                }
            }
        }
    )
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid',
        from_attributes=True
    )
    
    def __init__(self, **data):
        """Initialize ThreeFileSplitConfig."""
        # Remove name field if present as it's not part of our schema
        if 'name' in data:
            del data['name']
        super().__init__(**data)
        
    def validate_options(self) -> List[str]:
        """Validate processor options."""
        errors = super().validate_options()
        if not self.enabled:
            return errors
            
        # Validate required components
        if 'components' not in self.options:
            errors.append("Missing required 'components' section in options")
            return errors
            
        components = self.options['components']
        if 'three_file_split_processor' not in components:
            errors.append("Missing required 'three_file_split_processor' component")
            return errors
            
        config = components['three_file_split_processor'].get('config', {})
        
        # Validate output files
        if 'output_files' not in config:
            errors.append("Missing required 'output_files' configuration")
        else:
            required_files = ['summary', 'raw_notes', 'attachments']
            for file_type in required_files:
                if file_type not in config['output_files']:
                    errors.append(f"Missing required output file type: {file_type}")
                    
        # Validate section markers
        if 'section_markers' not in config:
            errors.append("Missing required 'section_markers' configuration")
        else:
            required_markers = ['summary', 'raw_notes', 'attachments']
            for marker_type in required_markers:
                if marker_type not in config['section_markers']:
                    errors.append(f"Missing required section marker: {marker_type}")
                    
        # Validate attachment markers
        if 'attachment_markers' not in config:
            errors.append("Missing required 'attachment_markers' configuration")
        else:
            required_markers = ['start', 'end']
            for marker_type in required_markers:
                if marker_type not in config['attachment_markers']:
                    errors.append(f"Missing required attachment marker: {marker_type}")
                    
        return errors


class ThreeFileSplitProcessor(BaseProcessor):
    """Processor for splitting markdown files into three sections."""
    
    def __init__(
        self,
        processor_config: ProcessorConfig,
        pipeline_config: PipelineConfig,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        console: Optional[Console] = None
    ):
        """Initialize the processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
            timing: Optional timing utility
            metrics: Optional metrics tracker
            console: Optional console logger
        """
        super().__init__(processor_config, pipeline_config, timing, metrics, console)
        self.section_files = processor_config.options.get('section_files', [
            'summary.md',
            'raw_notes.md',
            'attachments.md'
        ])
        self.preserve_metadata = processor_config.options.get('preserve_metadata', True)
        self.track_relationships = processor_config.options.get('track_relationships', True)
        
    async def setup(self) -> None:
        """Set up the processor."""
        self._initialize()
        
    async def process(self) -> ProcessingResult:
        """Process the input file.
        
        Returns:
            ProcessingResult containing processing results
        """
        try:
            input_file = Path(self.input_dir) / "all_merged_markdown.md"
            if not input_file.exists():
                return ProcessingResult(
                    success=False,
                    errors=[f"Input file not found: {input_file}"]
                )
            
            # Process the file
            await self._process(str(input_file))
            
            # Create result
            result = ProcessingResult(
                success=len(self.errors) == 0,
                processed_files=[Path(p) for p in self.processed_files],
                errors=self.errors
            )
            
            # Add metadata
            result.metadata.update({
                'failed_files': list(self.failed_files),
                'skipped_files': list(self.skipped_files),
                'section_files': self.section_files
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing files: {str(e)}"
            self.errors.append(error_msg)
            self.console.print(f"[red]{error_msg}[/red]")
            return ProcessingResult(
                success=False,
                errors=self.errors,
                metadata={
                    'processed_files': list(self.processed_files),
                    'failed_files': list(self.failed_files),
                    'skipped_files': list(self.skipped_files)
                }
            )
            
    async def _process(self, file_path: str) -> None:
        """Process a single file.
        
        Args:
            file_path: Path to the file to process
        """
        try:
            # Read input file
            content = Path(file_path).read_text()
            
            # Extract metadata if present
            metadata = {}
            if '<!--' in content and '-->' in content:
                try:
                    metadata_str = content[content.find('<!--')+4:content.find('-->')]
                    metadata = json.loads(metadata_str)
                except json.JSONDecodeError:
                    self.errors.append(f"Failed to parse metadata in {file_path}")
                    return
            
            # Split content by markers
            sections = {
                'summary': [],
                'raw_notes': [],
                'attachments': []
            }
            
            current_section = None
            for line in content.split('\n'):
                if line.startswith('--=='):
                    if 'SUMMARY' in line:
                        current_section = 'summary'
                    elif 'RAW NOTES' in line:
                        current_section = 'raw_notes'
                    elif 'ATTACHMENTS' in line:
                        current_section = 'attachments'
                elif current_section:
                    sections[current_section].append(line)
            
            # Write output files
            for section, lines in sections.items():
                if not lines:
                    continue
                    
                output_file = Path(self.output_dir) / f"{section}.md"
                
                # Add metadata
                section_metadata = {
                    'document': {
                        'processor': 'ThreeFileSplitProcessor',
                        'version': '1.0',
                        'timestamp': datetime.now().isoformat(),
                        'section': section
                    }
                }
                
                if self.preserve_metadata:
                    section_metadata.update(metadata)
                
                # Write file
                with output_file.open('w') as f:
                    f.write(f"<!--{json.dumps(section_metadata)}-->\n\n")
                    f.write('\n'.join(lines))
                
                self.processed_files.add(str(output_file))
                self.metrics.increment('files_processed')
                
        except Exception as e:
            self.failed_files.add(file_path)
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.errors.append(error_msg)
            self.console.print(f"[red]{error_msg}[/red]")
            
    def _initialize(self) -> None:
        """Initialize the processor."""
        # Verify output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
    def _cleanup(self) -> None:
        """Clean up resources."""
        pass 