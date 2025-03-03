# Nova CLI Quick Reference

## Installation

```bash
uv pip install nova
```

## Commands

### Help

```bash
nova --help
nova consolidate-markdown --help
nova upload-markdown --help
```

### Version

```bash
nova --version
```

### Consolidate Markdown

```bash
nova consolidate-markdown
```

With specific config:

```bash
nova consolidate-markdown --config /path/to/nova.toml
```

### Upload Markdown

```bash
nova upload-markdown
```

With specific config:

```bash
nova upload-markdown --config /path/to/nova.toml
```

With dry run:

```bash
nova upload-markdown --dry-run
```

Override output directory:

```bash
nova upload-markdown --output-dir /path/to/output
```

Delete existing content before uploading:

```bash
nova upload-markdown --delete-existing
```

## Configuration File

### Unified Configuration (`nova.toml`)

```toml
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
api_provider = "openrouter"

# Model Configuration
[consolidate.models]
default_model = "gpt-4o"

# Source Configurations
[[consolidate.sources]]
type = "bear"
srcDir = "/path/to/input/bear/notes"
destDir = "/path/to/output/bear/notes"

# Upload Configuration
[upload]
output_dir = "/path/to/output/directory"
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `3`: Consolidation error
- `4`: Upload error
- `5`: Graphlit client error
- `130`: Keyboard interrupt (Ctrl+C)

## Common Issues

| Error | Solution |
|-------|----------|
| Configuration file not found | Verify the file path |
| Invalid configuration | Check for missing or invalid fields |
| Source directory not found | Verify the directory exists |
| Output directory not found | Verify the directory exists |
| Graphlit API errors | Check your API credentials |

## Workflow Example

```bash
# Step 1: Consolidate Markdown files
nova consolidate-markdown

# Step 2: Upload the consolidated files to Graphlit
nova upload-markdown
```
