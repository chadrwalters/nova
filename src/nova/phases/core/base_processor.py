"""Base processor implementation."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, List

from nova.core.config import ProcessorConfig, PipelineConfig
from nova.core.utils.progress import ProgressTracker, ProcessingStatus

logger = logging.getLogger(__name__)

class ProcessorResult:
    """Result of a processor operation."""
    
    def __init__(
        self,
        success: bool = False,
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        processed_files: Optional[List[Path]] = None
    ):
        self.success = success
        self.content = content
        self.metadata = metadata or {}
        self.errors = errors or []
        self.processed_files = processed_files or []

    @property
    def processed_file_count(self) -> int:
        """Get the number of processed files."""
        return len(self.processed_files)

class BaseProcessor:
    """Base class for all processors."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize the processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        self.processor_config = processor_config
        self.pipeline_config = pipeline_config
        self.progress_tracker = ProgressTracker()
        
        # Find phase ID from config
        self.phase_id = None
        for phase in pipeline_config.phases:
            if phase.processor == processor_config.processor:
                self.phase_id = phase.name
                break
        
        if self.phase_id is None:
            raise ValueError(f"Could not find phase ID for processor {processor_config.processor}")
    
    def _start_phase(self, total_files: int, description: Optional[str] = None) -> None:
        """Start tracking a new phase.
        
        Args:
            total_files: Total number of files to process
            description: Optional phase description
        """
        desc = description or self.processor_config.description or f"Processing phase {self.phase_id}"
        self.progress_tracker.start_task(
            task_id=self.phase_id,
            description=desc,
            total_files=total_files
        )
    
    def _update_phase_progress(
        self,
        status: Optional[ProcessingStatus] = None,
        current_file: Optional[str] = None,
        processed_files: Optional[int] = None,
        cached_files: Optional[int] = None,
        skipped_files: Optional[int] = None,
        failed_files: Optional[int] = None,
        error_message: Optional[str] = None,
        **metadata
    ) -> None:
        """Update phase progress.
        
        Args:
            status: Current processing status
            current_file: Current file being processed
            processed_files: Number of processed files
            cached_files: Number of cached files
            skipped_files: Number of skipped files
            failed_files: Number of failed files
            error_message: Optional error message
            **metadata: Additional metadata
        """
        self.progress_tracker.update_task(
            task_id=self.phase_id,
            status=status,
            current_file=current_file,
            processed_files=processed_files,
            cached_files=cached_files,
            skipped_files=skipped_files,
            failed_files=failed_files,
            error_message=error_message
        )
    
    def _complete_phase(
        self,
        error_message: Optional[str] = None,
        status: Optional[ProcessingStatus] = None
    ) -> None:
        """Complete the current phase.
        
        Args:
            error_message: Optional error message
            status: Optional final status
        """
        if error_message:
            status = ProcessingStatus.FAILED
        elif status is None:
            status = ProcessingStatus.COMPLETED

        self.progress_tracker.complete_task(
            task_id=self.phase_id,
            status=status
        )
    
    def get_phase_progress(self) -> Dict[str, Any]:
        """Get current phase progress.
        
        Returns:
            Dictionary containing phase progress information
        """
        try:
            task = self.progress_tracker.get_task(self.phase_id)
            if task:
                return {
                    'phase_id': self.phase_id,
                    'description': task.description,
                    'status': task.status_value,
                    'total_files': task.total_files,
                    'processed_files': task.processed_files,
                    'cached_files': task.cached_files,
                    'skipped_files': task.skipped_files,
                    'failed_files': task.failed_files,
                    'elapsed_time': task.elapsed_time,
                    'current_file': task.current_file,
                    'error_message': task.error_message
                }
            else:
                return {
                    'phase_id': self.phase_id,
                    'status': 'not_started',
                    'error': 'Phase not started'
                }
        except Exception as e:
            logger.error(f"Error getting phase progress: {str(e)}")
            return {
                'phase_id': self.phase_id,
                'status': 'error',
                'error': str(e)
            }
    
    async def process(
        self,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessorResult:
        """Process files.
        
        This method should be implemented by subclasses.
        
        Args:
            input_dir: Input directory
            output_dir: Output directory
            context: Processing context
            
        Returns:
            ProcessorResult containing success/failure and any errors
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement process method") 