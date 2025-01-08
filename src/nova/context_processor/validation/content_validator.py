"""Content validation for Nova document processor."""

import logging
import mimetypes
import magic
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..core.errors import ValidationError
from ..core.metadata import BaseMetadata

logger = logging.getLogger(__name__)


class ContentValidator:
    """Validator for file contents."""

    def __init__(self):
        """Initialize validator."""
        self.mime = magic.Magic(mime=True)

    def validate_file(self, file_path: Path, metadata: Optional[BaseMetadata] = None) -> List[ValidationError]:
        """Validate a file's content.

        Args:
            file_path: Path to file
            metadata: Optional metadata for additional validation

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Basic file checks
            if not file_path.exists():
                errors.append(ValidationError(
                    message="File does not exist",
                    file_path=file_path,
                    details={"path": str(file_path)},
                    recovery_hint="Check if file was moved or deleted."
                ))
                return errors

            if not file_path.is_file():
                errors.append(ValidationError(
                    message="Path is not a file",
                    file_path=file_path,
                    details={"path": str(file_path)},
                    recovery_hint="Check if path points to a directory or special file."
                ))
                return errors

            # Size checks
            file_size = file_path.stat().st_size
            if file_size == 0:
                errors.append(ValidationError(
                    message="File is empty",
                    file_path=file_path,
                    details={"size": 0},
                    recovery_hint="Check if file was properly created."
                ))

            # MIME type validation
            detected_mime = self.mime.from_file(str(file_path))
            expected_mime = mimetypes.guess_type(str(file_path))[0]
            
            if expected_mime and detected_mime != expected_mime:
                errors.append(ValidationError(
                    message="File content does not match extension",
                    file_path=file_path,
                    details={
                        "detected_mime": detected_mime,
                        "expected_mime": expected_mime
                    },
                    recovery_hint="Check if file extension is correct for the content type."
                ))

            # Metadata validation
            if metadata:
                # Check file size consistency
                if metadata.file_size != file_size:
                    errors.append(ValidationError(
                        message="File size mismatch",
                        file_path=file_path,
                        details={
                            "actual_size": file_size,
                            "metadata_size": metadata.file_size
                        },
                        recovery_hint="Update metadata with correct file size."
                    ))

                # Check file hash if present
                if metadata.file_hash:
                    from ..utils.file_utils import calculate_file_hash
                    current_hash = calculate_file_hash(file_path)
                    if current_hash != metadata.file_hash:
                        errors.append(ValidationError(
                            message="File hash mismatch",
                            file_path=file_path,
                            details={
                                "current_hash": current_hash,
                                "metadata_hash": metadata.file_hash
                            },
                            recovery_hint="File may have been modified. Update metadata hash."
                        ))

            # Content encoding check for text files
            if detected_mime and detected_mime.startswith('text/'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.read()
                except UnicodeDecodeError:
                    errors.append(ValidationError(
                        message="Invalid text file encoding",
                        file_path=file_path,
                        details={"mime_type": detected_mime},
                        recovery_hint="Convert file to UTF-8 encoding."
                    ))

            return errors

        except Exception as e:
            errors.append(ValidationError(
                message=f"Validation failed: {str(e)}",
                file_path=file_path,
                details={"error": str(e)},
                recovery_hint="Check file permissions and system configuration."
            ))
            return errors

    def validate_markdown_content(self, content: str, file_path: Path) -> List[ValidationError]:
        """Validate markdown content.

        Args:
            content: Markdown content to validate
            file_path: Path to source file

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Check for empty content
            if not content.strip():
                errors.append(ValidationError(
                    message="Empty markdown content",
                    file_path=file_path,
                    recovery_hint="Add content to the markdown file."
                ))
                return errors

            # Check for basic markdown structure
            if not any(line.startswith('#') for line in content.splitlines()):
                errors.append(ValidationError(
                    message="Missing markdown headings",
                    file_path=file_path,
                    recovery_hint="Add appropriate headings to structure the content."
                ))

            # Check for broken links
            link_errors = self._validate_markdown_links(content, file_path)
            errors.extend(link_errors)

            # Check for code block syntax
            if '```' in content:
                code_block_errors = self._validate_code_blocks(content, file_path)
                errors.extend(code_block_errors)

            return errors

        except Exception as e:
            errors.append(ValidationError(
                message=f"Markdown validation failed: {str(e)}",
                file_path=file_path,
                details={"error": str(e)},
                recovery_hint="Check markdown syntax and content."
            ))
            return errors

    def _validate_markdown_links(self, content: str, file_path: Path) -> List[ValidationError]:
        """Validate markdown links.

        Args:
            content: Markdown content
            file_path: Path to source file

        Returns:
            List of validation errors
        """
        import re
        errors = []
        
        # Find all markdown links
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        links = re.finditer(link_pattern, content)
        
        for link in links:
            text, url = link.groups()
            
            # Skip external URLs
            if url.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                continue
                
            # Check relative file links
            if not url.startswith('#'):
                target_path = (file_path.parent / url).resolve()
                if not target_path.exists():
                    errors.append(ValidationError(
                        message=f"Broken link: {url}",
                        file_path=file_path,
                        details={
                            "link_text": text,
                            "target_path": str(target_path)
                        },
                        recovery_hint="Update or remove the broken link."
                    ))
        
        return errors

    def _validate_code_blocks(self, content: str, file_path: Path) -> List[ValidationError]:
        """Validate markdown code blocks.

        Args:
            content: Markdown content
            file_path: Path to source file

        Returns:
            List of validation errors
        """
        errors = []
        lines = content.splitlines()
        in_code_block = False
        code_block_start = 0
        
        for i, line in enumerate(lines, 1):
            if line.startswith('```'):
                if in_code_block:
                    in_code_block = False
                else:
                    in_code_block = True
                    code_block_start = i
                    
        if in_code_block:
            errors.append(ValidationError(
                message="Unclosed code block",
                file_path=file_path,
                details={"line_number": code_block_start},
                recovery_hint="Add closing ``` to the code block."
            ))
            
        return errors 