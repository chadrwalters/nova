"""Error tracking module for pipeline operations."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class ErrorDetails:
    """Standardized error details structure"""
    component: str                # The component that generated the error
    message: str                 # The error message
    context: Dict[str, Any]      # Contextual info like function, path, etc.
    timestamp: float             # When the error occurred
    is_critical: bool = False    # Whether this is a critical error
    parent_error: Optional['ErrorDetails'] = None  # For hierarchical errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            'component': self.component,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp,
            'is_critical': self.is_critical,
            'parent': self.parent_error.to_dict() if self.parent_error else None
        }

@dataclass
class WarningDetails:
    """Standardized warning details structure"""
    component: str                # The component that generated the warning
    message: str                 # The warning message
    context: Dict[str, Any]      # Contextual info like function, path, etc.
    timestamp: float             # When the warning occurred
    parent_warning: Optional['WarningDetails'] = None  # For hierarchical warnings

    def to_dict(self) -> Dict[str, Any]:
        return {
            'component': self.component,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp,
            'parent': self.parent_warning.to_dict() if self.parent_warning else None
        }

class ErrorTracker:
    """Tracks errors and warnings during pipeline operations."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize error tracker.
        
        Args:
            logger: Optional logger instance to use
        """
        self.errors: List[ErrorDetails] = []
        self.warnings: List[WarningDetails] = []
        self.logger = logger or logging.getLogger(__name__)
        
    def add_error(self, 
                 component: str, 
                 message: str, 
                 context: Optional[Dict[str, Any]] = None,
                 is_critical: bool = False,
                 parent_error: Optional[ErrorDetails] = None) -> None:
        """Add an error to the tracker.
        
        Args:
            component: Component that generated the error
            message: Error message
            context: Additional error context
            is_critical: Whether this is a critical error
            parent_error: Parent error for hierarchical tracking
        """
        error = ErrorDetails(
            component=component,
            message=message,
            context=context or {},
            timestamp=datetime.now().timestamp(),
            is_critical=is_critical,
            parent_error=parent_error
        )
        
        self.errors.append(error)
        self.logger.error(f"Error in {component}: {message} ({component}.{context.get('function', 'unknown') if context else 'unknown'}: {context if context else {}})")

    def add_warning(self, 
                   component: str, 
                   message: str, 
                   context: Optional[Dict[str, Any]] = None,
                   parent_warning: Optional[WarningDetails] = None) -> None:
        """Add a warning to the tracker.
        
        Args:
            component: Component that generated the warning
            message: Warning message
            context: Additional warning context
            parent_warning: Parent warning for hierarchical tracking
        """
        warning = WarningDetails(
            component=component,
            message=message,
            context=context or {},
            timestamp=datetime.now().timestamp(),
            parent_warning=parent_warning
        )
        
        self.warnings.append(warning)
        self.logger.warning(f"Warning in {component}: {message} ({component}.{context.get('function', 'unknown') if context else 'unknown'}: {context if context else {}})")
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get all tracked errors.
        
        Returns:
            List of error dictionaries
        """
        return [error.to_dict() for error in self.errors]

    def get_warnings(self) -> List[Dict[str, Any]]:
        """Get all tracked warnings.
        
        Returns:
            List of warning dictionaries
        """
        return [warning.to_dict() for warning in self.warnings]
    
    def get_error_report(self) -> Dict[str, Any]:
        """Get a report of all errors and warnings.
        
        Returns:
            Dictionary containing error report details
        """
        errors = self.get_errors()
        warnings = self.get_warnings()
        
        return {
            'total_errors': len(errors),
            'total_warnings': len(warnings),
            'errors': errors,
            'warnings': warnings,
            'has_errors': bool(errors),
            'has_warnings': bool(warnings),
            'components': list(set(err['component'] for err in errors).union(
                set(warn['component'] for warn in warnings)
            ))
        }

    def has_errors(self) -> bool:
        """Check if any errors are tracked.
        
        Returns:
            True if there are any errors, False otherwise
        """
        return bool(self.errors)
    
    def has_critical_errors(self) -> bool:
        """Check if any critical errors are tracked.
        
        Returns:
            True if there are any critical errors, False otherwise
        """
        return any(error.is_critical for error in self.errors)

    def clear(self) -> None:
        """Clear all tracked errors and warnings."""
        self.errors.clear()
        self.warnings.clear() 