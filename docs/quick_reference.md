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
nova consolidate-markdown --config /path/to/consolidate-markdown.toml
```

### Upload Markdown

```bash
nova upload-markdown --config /path/to/upload-markdown.toml --output-dir /path/to/output
```

With dry run:

```bash
nova upload-markdown --config /path/to/upload-markdown.toml --output-dir /path/to/output --dry-run
```

## Configuration Files

### Consolidate Markdown Configuration (`consolidate-markdown.toml`)

```toml
source_dir = "/path/to/source"
output_dir = "/path/to/output"
include_patterns = ["**/*.md"]
exclude_patterns = ["**/excluded/**"]

[logging]
level = "INFO"
```

### Upload Markdown Configuration (`upload-markdown.toml`)

```toml
[graphlit]
organization_id = "your-organization-id"
environment_id = "your-environment-id"
jwt_secret = "your-jwt-secret"

[logging]
level = "INFO"
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
nova consolidate-markdown --config ./consolidate-markdown.toml

# Step 2: Upload the consolidated files to Graphlit
nova upload-markdown --config ./upload-markdown.toml --output-dir ./output
```
