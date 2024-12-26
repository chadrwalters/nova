"""Base processor implementation."""

from pathlib import Path
from typing import Dict, Any, Optional, List

from nova.core.config import ProcessorConfig, PipelineConfig
from nova.core.logging import get_logger
from nova.core.utils.progress import ProgressTracker, ProcessingStatus
from nova.models.parsed_result import ProcessingResult

logger = get_logger(__name__)

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
    
    def __init__(self, config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize processor.
        
        Args:
            config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        self.config = config
        self.pipeline_config = pipeline_config
        self.phase_id = config.name
        self.logger = get_logger(self.__class__.__name__)
        self.progress_tracker = ProgressTracker()
        
    def _start_phase(self, total_files: int, description: Optional[str] = None) -> None:
        """Start tracking a new phase.
        
        Args:
            total_files: Total number of files to process
            description: Optional phase description
        """
        desc = description or self.config.description or f"Processing phase {self.phase_id}"
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
        # Update progress tracker
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
        
        # Calculate progress percentage
        task = self.progress_tracker.get_task(self.phase_id)
        if task and task.total_files > 0:
            progress = int((task.processed_files + task.cached_files) * 100 / task.total_files)
        else:
            progress = 0
        
        # Get total files being processed
        total_files = task.total_files if task else 0
        
        # Emit progress message
        logger.info(
            f"Phase {self.phase_id}: {progress}% - {status.value if status else 'UNKNOWN'} - {total_files} files"
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
        
    async def setup(self) -> None:
        """Set up processor."""
        pass
        
    async def process(self) -> ProcessingResult:
        """Process files.
        
        Returns:
            ProcessingResult containing processing results
        """
        raise NotImplementedError
        
    async def cleanup(self) -> None:
        """Clean up processor."""
        pass 