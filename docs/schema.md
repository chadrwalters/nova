# Nova Pipeline Configuration Schema

## Overview

The Nova pipeline configuration uses a JSON Schema to validate pipeline configurations. This document describes the schema structure, validation rules, and provides examples of valid configurations.

## Schema Structure

### Core Components

The pipeline configuration consists of two main sections:

1. Pipeline Definition
2. Component Configurations

```yaml
pipeline:
  components:    # Component configurations
    ...
  phases:        # Pipeline phases
    ...
```

### Required Fields

#### Pipeline Section
- `components`: Object containing component configurations
- `phases`: Array of phase configurations

#### Phase Configuration
- `description`: String describing the phase
- `output_dir`: String specifying output directory
- `processor`: String specifying processor class name
- `enabled`: Boolean indicating if phase is enabled
- `handlers`: Array of handler configurations

#### Component Configuration
- `parser`: String specifying parser version
- `config`: Object containing component-specific settings

## Validation Rules

### Schema Validation

The schema validator checks:
1. Required fields presence
2. Field types and formats
3. Enum value validation
4. Pattern matching
5. Numeric ranges

### Error Handling and Reporting

The validation system provides comprehensive error reporting through the following mechanisms:

1. **Error Tracking**
   - Tracks validation errors across components
   - Preserves error context and details
   - Supports critical and non-critical errors
   - Maintains error history until explicitly cleared

2. **Warning System**
   - Tracks potential issues that don't prevent execution
   - Provides guidance for configuration improvements
   - Maintains warning context and source

3. **Validation Reports**
   - Detailed validation status
   - Error counts and descriptions
   - Warning summaries
   - Component-specific validation results

4. **Error Context**
   - Path to error location
   - Schema path for validation errors
   - Component identification
   - Error criticality level

### Example Validation Report
```json
{
    "is_valid": false,
    "total_errors": 2,
    "total_warnings": 1,
    "errors": [
        {
            "message": "Missing required field 'output_dir' in phase TEST_PHASE",
            "context": {
                "path": "pipeline -> phases -> TEST_PHASE",
                "schema_path": "properties -> output_dir",
                "component": "schema_validator",
                "is_critical": true
            }
        }
    ],
    "warnings": [
        {
            "message": "Deprecated configuration option used",
            "context": {
                "component": "pipeline_manager",
                "is_critical": false
            }
        }
    ]
}
```

### Component Validation

Component configurations are validated for:
1. Required components per phase
2. Component dependencies
3. Version compatibility
4. Configuration structure

### Phase Validation

Phase configurations are validated for:
1. Unique phase names
2. Valid output directories
3. Handler configurations
4. Phase dependencies

## Error Handling

### Error Types

1. `ConfigurationError`: Invalid configuration structure
2. `ComponentError`: Invalid component configuration
3. `ProcessingError`: Runtime processing errors

### Warning Categories

1. Missing optional fields
2. Non-standard configurations
3. Deprecated features
4. Performance recommendations

### Error Context

Errors include detailed context:
```python
{
    "component": "component_name",
    "operation": "operation_name",
    "details": {
        "error": "error_description",
        "location": "error_location"
    }
}
```

## Configuration Examples

### Valid Configuration

```yaml
pipeline:
  components:
    markdown_processor:
      parser: "markitdown==0.0.1a3"
      config:
        document_conversion: true
        image_processing: true
        metadata_preservation: true
  phases:
    - MARKDOWN_PARSE:
        description: "Parse markdown files"
        output_dir: "${NOVA_PHASE_MARKDOWN_PARSE}"
        processor: "MarkdownProcessor"
        enabled: true
        handlers:
          - type: "UnifiedHandler"
            base_handler: "nova.phases.core.base_handler.BaseHandler"
            options:
              document_conversion: true
```

### Component Configuration

```yaml
components:
  markdown_processor:
    parser: "markitdown==0.0.1a3"
    config:
      document_conversion: true
      image_processing: true
      metadata_preservation: true
  image_processor:
    formats:
      - png
      - jpg/jpeg
      - gif
      - webp
      - heic/HEIC
    operations:
      - format_conversion:
          heic_to_jpg: true
          optimize_quality: 85
      - size_optimization:
          preserve_aspect_ratio: true
          max_dimensions: [1920, 1080]
```

## Validation Process

1. **Schema Validation**
   - Load JSON Schema
   - Validate configuration structure
   - Check required fields
   - Validate field types

2. **Component Validation**
   - Check required components
   - Validate component configurations
   - Check dependencies
   - Apply default values

3. **Phase Validation**
   - Check phase names
   - Validate output directories
   - Check handler configurations
   - Validate dependencies

4. **Error Handling**
   - Collect validation errors
   - Generate warnings
   - Provide error context
   - Track error states

## Best Practices

1. **Configuration Structure**
   - Use environment variables for paths
   - Keep components modular
   - Follow naming conventions
   - Document custom configurations

2. **Error Handling**
   - Check validation reports
   - Handle warnings appropriately
   - Use error context for debugging
   - Implement retry mechanisms

3. **Component Management**
   - Version control dependencies
   - Document component changes
   - Test configuration changes
   - Monitor component health

4. **Testing**
   - Validate configurations before deployment
   - Test with sample data
   - Check error handling
   - Verify component interactions

## Command Line Tools

### YAML Validation

Use the `validate_yaml.py` script to validate configurations:

```bash
python scripts/validate_yaml.py config/pipeline_config.yaml
```

Options:
- `--strict`: Enable strict validation
- `--warnings`: Show warnings
- `--debug`: Show debug information

### Schema Generation

Generate JSON Schema from configuration:

```bash
python scripts/generate_schema.py config/default_config.yaml
```

## Integration

### Pipeline Manager

```python
from nova.core.pipeline.manager import PipelineManager

# Create pipeline manager
manager = PipelineManager()

# Load configuration
await manager.load_config(config)

# Check for warnings
report = manager.get_error_report()
if report['warnings']:
    print("Configuration warnings:", report['warnings'])

# Get component configuration
markdown_config = manager.get_component_config('markdown_processor')
```

### Error Handling

```python
try:
    await manager.load_config(config)
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    print(f"Context: {e.context}")
except ComponentError as e:
    print(f"Component error: {e}")
    print(f"Component: {e.context.component}")
``` 