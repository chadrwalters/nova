"""Error tracking module."""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Error:
    """Error information."""
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    phase: Optional[str] = None
    file: Optional[str] = None
    traceback: Optional[str] = None


class ErrorTracker:
    """Tracks errors during pipeline processing."""

    def __init__(self):
        """Initialize error tracker."""
        self.errors: Dict[str, List[Error]] = {}
        self.registered_phases: List[str] = []

    def register_phase(self, phase_name: str) -> None:
        """Register a phase for error tracking.
        
        Args:
            phase_name: Name of the phase to register
        """
        if phase_name not in self.registered_phases:
            self.registered_phases.append(phase_name)
            self.errors[phase_name] = []

    def add_error(
        self,
        message: str,
        phase: Optional[str] = None,
        file: Optional[str] = None,
        traceback: Optional[str] = None
    ) -> None:
        """Add an error.
        
        Args:
            message: Error message
            phase: Optional phase name where error occurred
            file: Optional file being processed when error occurred
            traceback: Optional error traceback
        """
        error = Error(
            message=message,
            phase=phase,
            file=file,
            traceback=traceback
        )

        if phase and phase in self.errors:
            self.errors[phase].append(error)
        else:
            # Store in general errors if no phase or unregistered phase
            if "general" not in self.errors:
                self.errors["general"] = []
            self.errors["general"].append(error)

    def get_errors(self, phase: Optional[str] = None) -> List[Error]:
        """Get errors for a phase or all errors.
        
        Args:
            phase: Optional phase name to get errors for
            
        Returns:
            List of errors
        """
        if phase:
            return self.errors.get(phase, [])
        
        # Return all errors if no phase specified
        all_errors = []
        for phase_errors in self.errors.values():
            all_errors.extend(phase_errors)
        return all_errors

    def has_errors(self, phase: Optional[str] = None) -> bool:
        """Check if there are any errors.
        
        Args:
            phase: Optional phase name to check errors for
            
        Returns:
            True if there are errors, False otherwise
        """
        return len(self.get_errors(phase)) > 0

    def clear(self, phase: Optional[str] = None) -> None:
        """Clear errors.
        
        Args:
            phase: Optional phase name to clear errors for
        """
        if phase:
            if phase in self.errors:
                self.errors[phase] = []
        else:
            for phase in self.errors:
                self.errors[phase] = []

    def get_registered_phases(self) -> List[str]:
        """Get list of registered phases.
        
        Returns:
            List of registered phase names
        """
        return self.registered_phases.copy() 