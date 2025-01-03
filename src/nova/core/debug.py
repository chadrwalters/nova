"""Debug functionality for Nova."""
import logging
import json
import traceback
import psutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from rich.console import Console
from rich.table import Table

from ..config.settings import DebugConfig
from .metrics import MetricsTracker


class DebugManager:
    """Manages debug functionality."""
    
    def __init__(self, config: DebugConfig):
        """Initialize debug manager.
        
        Args:
            config: Debug configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.metrics = MetricsTracker()
        self.state_snapshots: List[Dict] = []
        self.traced_files: Set[Path] = {Path(f) for f in config.trace_files}
        self.console = Console()
        
        # Initialize debug directory if needed
        if config.dump_dir:
            dump_dir = Path(config.dump_dir)
            dump_dir.mkdir(parents=True, exist_ok=True)
    
    def is_debug_enabled(self, phase: Optional[str] = None) -> bool:
        """Check if debug mode is enabled.
        
        Args:
            phase: Optional phase name to check specific phase flag
            
        Returns:
            Whether debug mode is enabled
        """
        if not self.config.enabled:
            return False
            
        if phase and phase in self.config.phase_flags:
            return self.config.phase_flags[phase]
            
        return True
    
    def should_trace_file(self, file_path: Path) -> bool:
        """Check if a file should be traced.
        
        Args:
            file_path: File path to check
            
        Returns:
            Whether file should be traced
        """
        if not self.config.enabled:
            return False
            
        return any(
            file_path.match(pattern)
            for pattern in self.config.trace_files
        )
    
    def take_state_snapshot(self, state: Dict, phase: str) -> None:
        """Take a snapshot of pipeline state.
        
        Args:
            state: Current pipeline state
            phase: Current phase
        """
        if not self.config.state_logging:
            return
            
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'phase': phase,
            'state': state
        }
        
        self.state_snapshots.append(snapshot)
        
        if self.config.dump_state and self.config.dump_dir:
            dump_file = Path(self.config.dump_dir) / f"state_{phase}_{len(self.state_snapshots)}.json"
            with open(dump_file, 'w') as f:
                json.dump(snapshot, f, indent=2, default=str)
    
    def log_memory_usage(self) -> Dict[str, float]:
        """Log current memory usage.
        
        Returns:
            Dictionary with memory metrics
        """
        if not self.config.memory_tracking:
            return {}
            
        process = psutil.Process()
        memory_info = process.memory_info()
        
        metrics = {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent()
        }
        
        self.logger.debug(
            "Memory usage: RSS=%.1fMB VMS=%.1fMB (%.1f%%)",
            metrics['rss'], metrics['vms'], metrics['percent']
        )
        
        return metrics
    
    def validate_state(self, state: Dict, phase: str) -> List[str]:
        """Perform extra validation on pipeline state.
        
        Args:
            state: Current pipeline state
            phase: Current phase
            
        Returns:
            List of validation errors
        """
        if not self.config.extra_validation:
            return []
            
        errors = []
        
        # Check for basic state structure
        if phase not in state:
            errors.append(f"Missing state for phase: {phase}")
            return errors
            
        phase_state = state[phase]
        
        # Check for required state fields
        required_fields = {
            'successful_files',
            'failed_files',
            'skipped_files',
            'unchanged_files',
            'reprocessed_files',
            'file_type_stats'
        }
        
        for field in required_fields:
            if field not in phase_state:
                errors.append(f"Missing required field in {phase} state: {field}")
        
        # Validate file sets
        file_sets = [
            'successful_files',
            'failed_files',
            'skipped_files',
            'unchanged_files',
            'reprocessed_files'
        ]
        
        for set_name in file_sets:
            if set_name in phase_state:
                file_set = phase_state[set_name]
                if not isinstance(file_set, set):
                    errors.append(f"{phase}.{set_name} should be a set")
                
                # Check for file existence
                for file_path in file_set:
                    if not Path(file_path).exists():
                        errors.append(f"File in {phase}.{set_name} does not exist: {file_path}")
        
        # Phase-specific validation
        if phase == 'parse':
            if 'attachments' not in phase_state:
                errors.append("Missing attachments tracking in parse state")
        elif phase == 'disassemble':
            if 'stats' not in phase_state:
                errors.append("Missing stats in disassemble state")
        elif phase == 'split':
            if 'section_stats' not in phase_state:
                errors.append("Missing section_stats in split state")
        
        return errors
    
    def print_debug_summary(self) -> None:
        """Print debug summary."""
        if not self.config.enabled:
            return
            
        # Create summary table
        table = Table(title="Debug Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")
        
        # Add debug configuration
        table.add_row("Debug Mode", "Enabled" if self.config.enabled else "Disabled")
        table.add_row("State Logging", "Enabled" if self.config.state_logging else "Disabled")
        table.add_row("Extra Validation", "Enabled" if self.config.extra_validation else "Disabled")
        table.add_row("Performance Tracking", "Enabled" if self.config.performance_tracking else "Disabled")
        table.add_row("Memory Tracking", "Enabled" if self.config.memory_tracking else "Disabled")
        
        # Add metrics summary if enabled
        if self.config.performance_tracking:
            metrics = self.metrics.get_metrics_summary()
            for operation, stats in metrics.items():
                table.add_row(
                    f"Operation: {operation}",
                    f"Avg: {stats['avg_time']:.2f}s ({stats['call_count']} calls)"
                )
        
        # Add memory stats if enabled
        if self.config.memory_tracking:
            memory_stats = self.log_memory_usage()
            table.add_row("Memory RSS", f"{memory_stats['rss']:.1f} MB")
            table.add_row("Memory %", f"{memory_stats['percent']:.1f}%")
        
        # Add state snapshot count
        if self.config.state_logging:
            table.add_row("State Snapshots", str(len(self.state_snapshots)))
        
        self.console.print(table)
    
    async def track_operation(self, operation: str, duration: float) -> None:
        """Track operation timing.
        
        Args:
            operation: Operation name
            duration: Operation duration in seconds
        """
        if self.config.performance_tracking:
            await self.metrics.record_operation(operation, duration)
    
    def handle_error(self, error: Exception, phase: str, file_path: Optional[Path] = None) -> bool:
        """Handle error in debug mode.
        
        Args:
            error: Exception that occurred
            phase: Current phase
            file_path: Optional file path where error occurred
            
        Returns:
            Whether to continue processing
        """
        if not self.config.enabled:
            return True
            
        # Log error with full traceback
        self.logger.error(
            "Error in %s%s:\n%s",
            phase,
            f" processing {file_path}" if file_path else "",
            "".join(traceback.format_exception(type(error), error, error.__traceback__))
        )
        
        # Take state snapshot if enabled
        if self.config.state_logging:
            self.logger.debug("Taking error state snapshot")
            # Note: Actual state snapshot would be taken by caller
        
        # Log memory usage if enabled
        if self.config.memory_tracking:
            self.logger.debug("Logging error memory state")
            self.log_memory_usage()
        
        # Break if configured
        if self.config.break_on_error:
            self.logger.info("Breaking on error as configured")
            return False
        
        return True 