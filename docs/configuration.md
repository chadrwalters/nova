# Nova Configuration System

## Overview

Nova uses a split configuration system with two main configuration files:

1. `config/default_config.yaml`: Global system configuration
2. `config/pipeline.yaml`: Pipeline-specific configuration

This split allows for better separation of concerns and makes it easier to manage different aspects of the system.

## Configuration Files

### Global Configuration (`default_config.yaml`)

The global configuration file handles system-wide settings that are not specific to the document processing pipeline. This includes:

- Logging configuration
- API configurations (OpenAI, etc.)
- Global retry policies
- Cache settings
- Other system-wide settings

Example:
```yaml
# Logging Configuration
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# OpenAI Configuration
openai:
  enabled: true
  model: "gpt-4-0125-preview"
  max_tokens: 500
```

### Pipeline Configuration (`pipeline.yaml`)

The pipeline configuration file contains all settings specific to the document processing pipeline. This includes:

- Pipeline phases and their order
- Component configurations
- Processing rules and handlers
- Input/output paths
- Phase-specific settings

Example:
```yaml
pipeline:
  paths:
    base_dir: "${NOVA_BASE_DIR}"
  components:
    markdown_processor:
      parser: "markitdown==0.0.1a3"
  phases:
    - MARKDOWN_PARSE:
        description: "Parse markdown files"
        output_dir: "${NOVA_PHASE_MARKDOWN_PARSE}"
```

## Why Split Configuration?

The configuration is split for several reasons:

1. **Separation of Concerns**
   - Global settings are separated from pipeline-specific settings
   - Makes it easier to modify one aspect without affecting others
   - Reduces the risk of accidental changes

2. **Maintainability**
   - Each configuration file has a clear, single responsibility
   - Easier to understand and modify specific parts of the system
   - Reduces cognitive load when making changes

3. **Flexibility**
   - Global settings can be shared across different pipeline configurations
   - Pipeline configurations can be swapped without changing system settings
   - Easier to create different pipeline configurations for different use cases

## Environment Variables

Both configuration files can reference environment variables using the `${VAR_NAME}` syntax. These variables should be defined in the `.env` file at the root of the project.

## Best Practices

1. **Global Configuration**
   - Keep system-wide settings in `default_config.yaml`
   - Avoid putting pipeline-specific settings here
   - Use this for third-party service configurations

2. **Pipeline Configuration**
   - Keep all pipeline-specific settings in `pipeline.yaml`
   - Use clear, descriptive names for phases and components
   - Document any non-obvious settings

3. **Environment Variables**
   - Use environment variables for paths and secrets
   - Keep sensitive information out of configuration files
   - Document required environment variables

## Modifying Configuration

When modifying configuration:

1. Always test changes in a development environment first
2. Document any new configuration options
3. Update both files if needed, maintaining the separation of concerns
4. Validate configuration changes using the built-in validation system

## Configuration Validation

The system validates configuration files on startup:

1. Schema validation ensures all required fields are present
2. Type checking ensures values are of the correct type
3. Component validation ensures all required components are available
4. Path validation ensures all required directories exist or can be created

## Troubleshooting

Common configuration issues and their solutions:

1. **Missing Fields**: Check schema documentation for required fields
2. **Invalid Values**: Ensure values match expected types
3. **Path Issues**: Verify environment variables are set correctly
4. **Component Errors**: Check component dependencies and configurations 