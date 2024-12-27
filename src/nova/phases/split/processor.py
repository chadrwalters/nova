"""Three-file split processor."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from nova.core.pipeline.errors import ValidationError
from nova.core.pipeline.types import ProcessingResult
from nova.core.pipeline.base_handler import BaseHandler


class ThreeFileSplitProcessor:
    """Processor for splitting content into three files."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize processor.
        
        Args:
            config: Processor configuration
        """
        self.config = config or {}
        self.output_dir = self.config.get('output_dir')
        self.options = self.config.get('options', {})
        self.logger = logging.getLogger(__name__)

    def validate(self) -> None:
        """Validate processor configuration.
        
        Raises:
            ValidationError: If validation fails
        """
        if not self.output_dir:
            raise ValidationError("Output directory is required")

    async def process(self, input_files: List[Path]) -> ProcessingResult:
        """Process input files.
        
        Args:
            input_files: List of input files
            
        Returns:
            Processing result
        """
        try:
            # Validate configuration
            self.validate()

            # Initialize result
            result = ProcessingResult(
                success=True,
                processed_files=[],
                metadata={},
                content=None
            )

            # Process each file
            for file_path in input_files:
                file_result = await self._process_file(file_path)
                if not file_result.success:
                    result.success = False
                    result.errors.extend(file_result.errors)
                    continue

                result.processed_files.extend(file_result.processed_files)
                result.metadata.update(file_result.metadata)

            return result

        except Exception as e:
            error_msg = f"Error in processor: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                errors=[error_msg]
            )

    async def _process_file(self, file_path: Path) -> ProcessingResult:
        """Process a single file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Processing result
        """
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8')

            # Split content into sections
            summary, raw_notes, attachments = self._split_content(content)

            # Create output files
            output_files = []
            output_dir = Path(self.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Write summary
            summary_path = output_dir / 'summary.md'
            summary_path.write_text(summary, encoding='utf-8')
            output_files.append(summary_path)

            # Write raw notes
            raw_notes_path = output_dir / 'raw_notes.md'
            raw_notes_path.write_text(raw_notes, encoding='utf-8')
            output_files.append(raw_notes_path)

            # Write attachments
            attachments_path = output_dir / 'attachments.md'
            attachments_path.write_text(attachments, encoding='utf-8')
            output_files.append(attachments_path)

            return ProcessingResult(
                success=True,
                processed_files=output_files,
                metadata={
                    'summary_size': len(summary),
                    'raw_notes_size': len(raw_notes),
                    'attachments_size': len(attachments)
                },
                content=content
            )

        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                errors=[error_msg]
            )

    def _split_content(self, content: str) -> tuple[str, str, str]:
        """Split content into three sections.
        
        Args:
            content: Content to split
            
        Returns:
            Tuple of (summary, raw_notes, attachments)
        """
        # Initialize sections
        summary = []
        raw_notes = []
        attachments = []
        current_section = summary

        # Process content line by line
        for line in content.split('\n'):
            # Check for section markers
            if line.startswith('--==SUMMARY==--'):
                current_section = summary
                continue
            elif line.startswith('--==RAW NOTES==--'):
                current_section = raw_notes
                continue
            elif line.startswith('--==ATTACHMENTS==--'):
                current_section = attachments
                continue
            elif line.startswith('--==ATTACHMENT_BLOCK:'):
                current_section = attachments

            # Add line to current section
            current_section.append(line)

        # Join sections
        return (
            '\n'.join(summary).strip(),
            '\n'.join(raw_notes).strip(),
            '\n'.join(attachments).strip()
        ) 