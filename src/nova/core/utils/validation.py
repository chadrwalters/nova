"""Validation utilities for Nova document processor."""

from pathlib import Path
from typing import Any, Dict, List, Type, Union, Optional

from ..errors import ValidationError


class Validator:
    """Validator for data validation."""
    
    @staticmethod
    def validate_path(
        path: Union[str, Path],
        must_exist: bool = False,
        must_be_file: bool = False,
        must_be_dir: bool = False
    ) -> Path:
        """Validate path.
        
        Args:
            path: Path to validate
            must_exist: Whether path must exist
            must_be_file: Whether path must be a file
            must_be_dir: Whether path must be a directory
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If validation fails
        """
        return validate_path(path, must_exist, must_be_file, must_be_dir)
    
    @staticmethod
    def validate_required_keys(data: Dict[str, Any], required_keys: List[str]) -> None:
        """Validate that dictionary contains required keys.
        
        Args:
            data: Dictionary to validate
            required_keys: List of required keys
            
        Raises:
            ValidationError: If validation fails
        """
        validate_required_keys(data, required_keys)
    
    @staticmethod
    def validate_type(value: Any, expected_type: Type) -> None:
        """Validate value type.
        
        Args:
            value: Value to validate
            expected_type: Expected type
            
        Raises:
            ValidationError: If validation fails
        """
        validate_type(value, expected_type)
    
    @staticmethod
    def validate_list_type(values: List[Any], expected_type: Type) -> None:
        """Validate type of all list elements.
        
        Args:
            values: List of values to validate
            expected_type: Expected type for elements
            
        Raises:
            ValidationError: If validation fails
        """
        validate_list_type(values, expected_type)
    
    @staticmethod
    def validate_dict_types(
        data: Dict[str, Any],
        type_map: Dict[str, Type]
    ) -> None:
        """Validate types of dictionary values.
        
        Args:
            data: Dictionary to validate
            type_map: Mapping of keys to expected types
            
        Raises:
            ValidationError: If validation fails
        """
        validate_dict_types(data, type_map)
    
    @staticmethod
    def validate_enum(value: Any, valid_values: List[Any]) -> None:
        """Validate that value is one of valid values.
        
        Args:
            value: Value to validate
            valid_values: List of valid values
            
        Raises:
            ValidationError: If validation fails
        """
        validate_enum(value, valid_values)
    
    @staticmethod
    def validate_range(
        value: Union[int, float],
        min_value: Union[int, float, None] = None,
        max_value: Union[int, float, None] = None
    ) -> None:
        """Validate that value is within range.
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Raises:
            ValidationError: If validation fails
        """
        validate_range(value, min_value, max_value)
    
    @staticmethod
    def validate_string(
        value: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None
    ) -> None:
        """Validate string value.
        
        Args:
            value: String to validate
            min_length: Minimum length
            max_length: Maximum length
            pattern: Regular expression pattern
            
        Raises:
            ValidationError: If validation fails
        """
        validate_string(value, min_length, max_length, pattern)


def validate_path(
    path: Union[str, Path],
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_dir: bool = False
) -> Path:
    """Validate path.
    
    Args:
        path: Path to validate
        must_exist: Whether path must exist
        must_be_file: Whether path must be a file
        must_be_dir: Whether path must be a directory
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Convert to Path
        path = Path(path)
        
        # Check existence
        if must_exist and not path.exists():
            raise ValidationError(f"Path does not exist: {path}")
        
        # Check file type
        if must_be_file and not path.is_file():
            raise ValidationError(f"Path is not a file: {path}")
            
        if must_be_dir and not path.is_dir():
            raise ValidationError(f"Path is not a directory: {path}")
        
        return path
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Invalid path {path}: {str(e)}") from e

def validate_required_keys(data: Dict[str, Any], required_keys: List[str]) -> None:
    """Validate that dictionary contains required keys.
    
    Args:
        data: Dictionary to validate
        required_keys: List of required keys
        
    Raises:
        ValidationError: If validation fails
    """
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValidationError(f"Missing required keys: {', '.join(missing_keys)}")

def validate_type(value: Any, expected_type: Type) -> None:
    """Validate value type.
    
    Args:
        value: Value to validate
        expected_type: Expected type
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"Invalid type: expected {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )

def validate_list_type(values: List[Any], expected_type: Type) -> None:
    """Validate type of all list elements.
    
    Args:
        values: List of values to validate
        expected_type: Expected type for elements
        
    Raises:
        ValidationError: If validation fails
    """
    for i, value in enumerate(values):
        try:
            validate_type(value, expected_type)
        except ValidationError as e:
            raise ValidationError(f"Invalid type at index {i}: {str(e)}") from e

def validate_dict_types(
    data: Dict[str, Any],
    type_map: Dict[str, Type]
) -> None:
    """Validate types of dictionary values.
    
    Args:
        data: Dictionary to validate
        type_map: Mapping of keys to expected types
        
    Raises:
        ValidationError: If validation fails
    """
    for key, expected_type in type_map.items():
        if key in data:
            try:
                validate_type(data[key], expected_type)
            except ValidationError as e:
                raise ValidationError(f"Invalid type for key {key}: {str(e)}") from e

def validate_enum(value: Any, valid_values: List[Any]) -> None:
    """Validate that value is one of valid values.
    
    Args:
        value: Value to validate
        valid_values: List of valid values
        
    Raises:
        ValidationError: If validation fails
    """
    if value not in valid_values:
        raise ValidationError(
            f"Invalid value: expected one of {valid_values}, got {value}"
        )

def validate_range(
    value: Union[int, float],
    min_value: Union[int, float, None] = None,
    max_value: Union[int, float, None] = None
) -> None:
    """Validate that value is within range.
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Raises:
        ValidationError: If validation fails
    """
    if min_value is not None and value < min_value:
        raise ValidationError(f"Value {value} is less than minimum {min_value}")
        
    if max_value is not None and value > max_value:
        raise ValidationError(f"Value {value} is greater than maximum {max_value}")

def validate_string(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None
) -> None:
    """Validate string value.
    
    Args:
        value: String to validate
        min_length: Minimum length
        max_length: Maximum length
        pattern: Regular expression pattern
        
    Raises:
        ValidationError: If validation fails
    """
    # Validate type
    validate_type(value, str)
    
    # Check length
    if min_length is not None and len(value) < min_length:
        raise ValidationError(f"String length {len(value)} is less than minimum {min_length}")
        
    if max_length is not None and len(value) > max_length:
        raise ValidationError(f"String length {len(value)} is greater than maximum {max_length}")
    
    # Check pattern
    if pattern is not None:
        import re
        if not re.match(pattern, value):
            raise ValidationError(f"String does not match pattern: {pattern}") 