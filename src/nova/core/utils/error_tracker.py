"""Error tracking utilities."""

from typing import Dict, List, Set


class ErrorTracker:
    """Track errors during pipeline execution."""
    
    def __init__(self):
        """Initialize error tracker."""
        self.phase_errors: Dict[str, List[str]] = {}
        self.registered_phases: Set[str] = set()
        
    def register_phase(self, phase_name: str) -> None:
        """Register a phase for error tracking.
        
        Args:
            phase_name: Name of phase to register
        """
        self.registered_phases.add(phase_name)
        self.phase_errors[phase_name] = []
        
    def add_phase_errors(self, phase_name: str, errors: List[str]) -> None:
        """Add errors for a phase.
        
        Args:
            phase_name: Name of phase
            errors: List of error messages
        """
        if phase_name not in self.phase_errors:
            self.register_phase(phase_name)
            
        self.phase_errors[phase_name].extend(errors)
        
    def get_phase_errors(self, phase_name: str) -> List[str]:
        """Get errors for a phase.
        
        Args:
            phase_name: Name of phase
            
        Returns:
            List of error messages
        """
        return self.phase_errors.get(phase_name, [])
        
    def get_registered_phases(self) -> Set[str]:
        """Get set of registered phases.
        
        Returns:
            Set of registered phase names
        """
        return self.registered_phases
        
    def has_errors(self, phase_name: str) -> bool:
        """Check if a phase has errors.
        
        Args:
            phase_name: Name of phase
            
        Returns:
            True if phase has errors, False otherwise
        """
        return bool(self.get_phase_errors(phase_name))
        
    def clear(self) -> None:
        """Clear all error tracking state."""
        self.phase_errors.clear()
        self.registered_phases.clear() 