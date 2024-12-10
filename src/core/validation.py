from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import chardet
import re
from typing import TypedDict, Final

from .exceptions import (
    ValidationError,
    FileSizeError,
    EncodingError,
    MalformedMarkdownError,
)

# Constants
MAX_FILE_SIZE_MB: Final[int] = 50
ALLOWED_ENCODINGS: Final[set[str]] = {
    "utf-8", 
    "ascii", 
    "utf-16",
    "windows-1252",  # Added Windows encoding
    "cp1252",        # Alternative name for windows-1252
    "latin-1",       # Common fallback encoding
    "iso-8859-1"     # Another common encoding
}
MAX_LINE_LENGTH: Final[int] = 10000

@dataclass
class ValidationResult:
    """Contains the results of file validation."""
    is_valid: bool
    encoding: str
    file_size: int
    error_message: Optional[str] = None

class MarkdownValidationRules(TypedDict):
    """Configuration for markdown validation rules."""
    max_file_size_mb: int
    allowed_encodings: set[str]
    max_line_length: int

async def validate_markdown_file(
    file_path: Path,
    rules: Optional[MarkdownValidationRules] = None,
    strict_hierarchy: bool = False
) -> ValidationResult:
    """
    Validates a markdown file for processing.

    Args:
        file_path: Path to the markdown file
        rules: Optional custom validation rules
        strict_hierarchy: Whether to enforce strict heading hierarchy

    Returns:
        ValidationResult object containing validation details

    Raises:
        ValidationError: If the file fails validation
    """
    if not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")

    if not rules:
        rules = MarkdownValidationRules(
            max_file_size_mb=MAX_FILE_SIZE_MB,
            allowed_encodings=ALLOWED_ENCODINGS,
            max_line_length=MAX_LINE_LENGTH
        )

    # Check file size
    file_size = file_path.stat().st_size
    if file_size > rules["max_file_size_mb"] * 1024 * 1024:
        raise FileSizeError(
            f"File size exceeds {rules['max_file_size_mb']}MB limit"
        )

    # Detect and validate encoding
    with file_path.open('rb') as f:
        raw_content = f.read()
        result = chardet.detect(raw_content)
        detected_encoding = result['encoding'].lower() if result['encoding'] else 'utf-8'
        
        # Try to decode with detected encoding first
        try:
            content = raw_content.decode(detected_encoding)
            encoding = detected_encoding
        except UnicodeDecodeError:
            # If detected encoding fails, try fallback encodings
            for fallback_encoding in ['utf-8', 'windows-1252', 'latin-1']:
                try:
                    content = raw_content.decode(fallback_encoding)
                    encoding = fallback_encoding
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise EncodingError(f"Could not decode file with any supported encoding")

    # Validate markdown content
    try:
        await validate_markdown_content(
            content, 
            rules["max_line_length"],
            strict_hierarchy=strict_hierarchy
        )
    except UnicodeDecodeError as e:
        raise EncodingError(f"Failed to decode file: {e}")

    return ValidationResult(
        is_valid=True,
        encoding=encoding,
        file_size=file_size
    )

async def validate_markdown_content(
    content: str, 
    max_line_length: int,
    strict_hierarchy: bool = False
) -> None:
    """
    Validates markdown content for common issues.

    Args:
        content: The markdown content to validate
        max_line_length: Maximum allowed line length
        strict_hierarchy: Whether to enforce strict heading hierarchy

    Raises:
        MalformedMarkdownError: If markdown content is malformed
    """
    lines = content.splitlines()
    
    # Check for common markdown issues
    heading_stack = []
    for line_num, line in enumerate(lines, 1):
        # Check line length
        if len(line) > max_line_length:
            raise MalformedMarkdownError(
                f"Line {line_num} exceeds maximum length of {max_line_length}"
            )

        # Validate heading hierarchy
        if line.startswith('#'):
            level = len(re.match(r'^#+', line).group())
            if level > 6:
                raise MalformedMarkdownError(
                    f"Invalid heading level {level} on line {line_num}"
                )
            
            # Only check hierarchy if strict mode is enabled
            if strict_hierarchy and heading_stack:
                if level > heading_stack[-1] + 1:
                    raise MalformedMarkdownError(
                        f"Invalid heading hierarchy on line {line_num}"
                    )
            heading_stack.append(level)

        # Validate code blocks
        if '```' in line:
            # Implementation for code block validation
            pass

        # Add more validation rules as needed