# Nova CLI User Guide

## Overview

Nova is a command-line tool designed to streamline the process of consolidating Markdown files and uploading them to Graphlit. It provides two main commands:

- `consolidate-markdown`: Consolidates Markdown files from a source directory into an output directory
- `upload-markdown`: Uploads Markdown files from an output directory to Graphlit

## Installation

### Prerequisites

- Python 3.8 or higher
- [UV](https://github.com/astral-sh/uv) for package management (recommended)

### Installing Nova

You can install Nova using UV:

```bash
uv pip install nova
```

Or using pip:

```bash
pip install nova
```

To install the development version directly from GitHub:

```bash
uv pip install git+https://github.com/username/nova.git
```

## Configuration

Nova uses a unified TOML configuration file for all commands. By default, Nova looks for a file named `nova.toml` in the current directory, but you can specify a different path using the `--config` option.

### Unified Configuration

Create a file named `nova.toml` by copying the template:

```bash
cp nova.toml.template nova.toml
```

Then edit it with your specific settings:

```toml
# Nova Unified Configuration File

# Graphlit API Configuration
[graphlit]
organization_id = "your-organization-id"
environment_id = "your-environment-id"
jwt_secret = "your-jwt-secret"

# Consolidate Markdown Configuration
[consolidate.global]
cm_dir = ".cm"
force_generation = false
no_image = false

# API Provider Configuration
api_provider = "openrouter"  # Options: "openai", "openrouter"

# OpenAI Configuration
openai_key = "your-openai-key"
openai_base_url = "https://api.openai.com/v1"

# OpenRouter Configuration
openrouter_key = "your-openrouter-key"
openrouter_base_url = "https://openrouter.ai/api/v1"

# Model Configuration
[consolidate.models]
default_model = "gpt-4o"  # Or your preferred model

# Source Configurations
[[consolidate.sources]]
type = "bear"
srcDir = "/path/to/input/bear/notes"
destDir = "/path/to/output/bear/notes"

# Upload Configuration
[upload]
output_dir = "/path/to/output/directory"
```

## Usage

### Consolidating Markdown Files

To consolidate Markdown files:

```bash
nova consolidate-markdown
```

Or with a specific configuration file:

```bash
nova consolidate-markdown --config /path/to/nova.toml
```

This command will:
1. Read Markdown files from the source directories specified in the configuration
2. Process them according to the configuration
3. Write the consolidated files to the destination directories

### Uploading Markdown Files to Graphlit

To upload Markdown files to Graphlit:

```bash
nova upload-markdown
```

Or with a specific configuration file:

```bash
nova upload-markdown --config /path/to/nova.toml
```

Options:
- `--output-dir`: Override the output directory specified in the configuration (optional)
- `--dry-run`: Simulate the upload process without actually uploading files
- `--delete-existing`: Delete all existing content in Graphlit before uploading

This command will:
1. Connect to Graphlit using the provided credentials
2. If `--delete-existing` is specified, delete all existing content in Graphlit
3. Find all Markdown files in the output directory
4. Upload each file to Graphlit

### Command-Line Help

For more information about available commands and options:

```bash
nova --help
nova consolidate-markdown --help
nova upload-markdown --help
```

## Examples

### Complete Workflow Example

This example demonstrates a complete workflow of consolidating and uploading Markdown files:

```bash
# Step 1: Consolidate Markdown files
nova consolidate-markdown

# Step 2: Upload the consolidated files to Graphlit
nova upload-markdown
```

### Dry Run Example

To test the upload process without actually uploading files:

```bash
nova upload-markdown --dry-run
```

### Delete Existing Content Example

To delete all existing content in Graphlit before uploading new files:

```bash
nova upload-markdown --delete-existing
```

This is useful when you want to refresh all content in Graphlit and avoid duplicates.

## Troubleshooting

### Common Issues

#### Configuration File Not Found

```
ConfigurationError: Configuration file not found: /path/to/config.toml
```

**Solution**: Verify that the configuration file exists at the specified path.

#### Invalid Configuration

```
ConfigurationError: Invalid configuration: field required (at output_dir)
```

**Solution**: Check your configuration file for missing or invalid fields.

#### Source Directory Not Found

```
ConsolidationError: Source directory not found: /path/to/source
```

**Solution**: Verify that the source directory exists and is accessible.

#### Output Directory Not Found

```
UploadError: Output directory not found: /path/to/output
```

**Solution**: Verify that the output directory exists and is accessible.

#### Graphlit API Errors

```
GraphlitClientError: Failed to initialize Graphlit client: Invalid credentials
```

**Solution**: Check your Graphlit API credentials in the configuration file.

### Logging

Nova uses structured logging to provide detailed information about its operations. You can adjust the logging level in the configuration file:

```toml
[logging]
level = "DEBUG"  # For more detailed logs
```

Log levels from least to most verbose:
- CRITICAL
- ERROR
- WARNING
- INFO (default)
- DEBUG

### Exit Codes

Nova uses the following exit codes:

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `3`: Consolidation error
- `4`: Upload error
- `5`: Graphlit client error
- `130`: Keyboard interrupt (Ctrl+C)

## Environment Variables

Nova does not use environment variables directly, but the underlying libraries might. Refer to the documentation of [consolidate-markdown](https://github.com/username/consolidate-markdown) and [graphlit](https://github.com/username/graphlit) for more information.

## Support

If you encounter any issues or have questions, please:

1. Check the troubleshooting section in this guide
2. Look for similar issues in the [GitHub repository](https://github.com/username/nova/issues)
3. Open a new issue if your problem is not already addressed
