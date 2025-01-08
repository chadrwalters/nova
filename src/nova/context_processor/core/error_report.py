"""Error reporting system for Nova document processor."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from .errors import ErrorContext, NovaError

logger = logging.getLogger(__name__)


class ErrorReport:
    """Error report for document processing."""

    def __init__(self, base_dir: Path):
        """Initialize error report.

        Args:
            base_dir: Base directory for reports
        """
        self.base_dir = base_dir
        self.report_dir = base_dir / "_NovaProcessing" / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.errors: List[Dict] = []
        self.error_files: Set[Path] = set()
        self.phase_errors: Dict[str, List[Dict]] = {}
        self.handler_errors: Dict[str, List[Dict]] = {}

    def add_error(
        self,
        error: NovaError,
        phase: Optional[str] = None,
        handler: Optional[str] = None,
    ) -> None:
        """Add an error to the report.

        Args:
            error: Error to add
            phase: Optional phase name
            handler: Optional handler name
        """
        error_dict = {
            "timestamp": datetime.now().isoformat(),
            "message": str(error),
            "category": error.context.category,
            "severity": error.context.severity,
            "file_path": str(error.context.file_path) if error.context.file_path else None,
            "details": error.context.details,
            "recovery_hint": error.context.recovery_hint,
            "phase": phase,
            "handler": handler,
        }

        # Add to main error list
        self.errors.append(error_dict)

        # Track error files
        if error.context.file_path:
            self.error_files.add(error.context.file_path)

        # Add to phase errors
        if phase:
            if phase not in self.phase_errors:
                self.phase_errors[phase] = []
            self.phase_errors[phase].append(error_dict)

        # Add to handler errors
        if handler:
            if handler not in self.handler_errors:
                self.handler_errors[handler] = []
            self.handler_errors[handler].append(error_dict)

    def generate_report(self) -> None:
        """Generate error report files."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report = {
                "generated_at": datetime.now().isoformat(),
                "total_errors": len(self.errors),
                "total_error_files": len(self.error_files),
                "errors_by_category": self._group_by_category(),
                "errors_by_severity": self._group_by_severity(),
                "errors_by_phase": self.phase_errors,
                "errors_by_handler": self.handler_errors,
                "error_files": [str(f) for f in sorted(self.error_files)],
                "errors": self.errors,
            }

            # Save detailed report
            report_path = self.report_dir / f"error_report_{timestamp}.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

            # Generate summary report
            self._generate_summary(report, timestamp)

            logger.info(f"Generated error report: {report_path}")

        except Exception as e:
            logger.error(f"Failed to generate error report: {str(e)}")

    def _group_by_category(self) -> Dict[str, List[Dict]]:
        """Group errors by category.

        Returns:
            Dict mapping categories to lists of errors
        """
        result: Dict[str, List[Dict]] = {}
        for error in self.errors:
            category = error["category"]
            if category not in result:
                result[category] = []
            result[category].append(error)
        return result

    def _group_by_severity(self) -> Dict[str, List[Dict]]:
        """Group errors by severity.

        Returns:
            Dict mapping severities to lists of errors
        """
        result: Dict[str, List[Dict]] = {}
        for error in self.errors:
            severity = error["severity"]
            if severity not in result:
                result[severity] = []
            result[severity].append(error)
        return result

    def _generate_summary(self, report: Dict, timestamp: str) -> None:
        """Generate summary report in markdown format.

        Args:
            report: Full error report
            timestamp: Report timestamp
        """
        summary_path = self.report_dir / f"error_summary_{timestamp}.md"
        
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("# Nova Processing Error Summary\n\n")
            f.write(f"Generated: {report['generated_at']}\n\n")
            
            f.write("## Overview\n")
            f.write(f"- Total Errors: {report['total_errors']}\n")
            f.write(f"- Files with Errors: {report['total_error_files']}\n\n")
            
            f.write("## Errors by Severity\n")
            for severity, errors in report["errors_by_severity"].items():
                f.write(f"### {severity}\n")
                f.write(f"- Count: {len(errors)}\n")
                for error in errors[:5]:  # Show first 5 errors of each severity
                    f.write(f"- {error['message']}\n")
                if len(errors) > 5:
                    f.write(f"- ... and {len(errors) - 5} more\n")
                f.write("\n")
            
            f.write("## Errors by Phase\n")
            for phase, errors in report["errors_by_phase"].items():
                f.write(f"### {phase}\n")
                f.write(f"- Count: {len(errors)}\n")
                for error in errors[:5]:
                    f.write(f"- {error['message']}\n")
                if len(errors) > 5:
                    f.write(f"- ... and {len(errors) - 5} more\n")
                f.write("\n")
            
            f.write("## Files with Errors\n")
            for file_path in sorted(report["error_files"])[:10]:
                f.write(f"- {file_path}\n")
            if len(report["error_files"]) > 10:
                f.write(f"- ... and {len(report['error_files']) - 10} more\n") 