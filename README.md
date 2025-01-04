# Nova Document Processing System

Nova is a document processing system that helps organize and analyze your documents.

## Features

- Process multiple document types (PDF, DOCX, MD, etc.)
- Generate summaries and insights
- Organize documents by topic
- Extract key information
- Process images with AI vision

## Installation

1. Clone the repository
2. Run `./install.sh` to set up dependencies
3. Configure Nova using `config/nova.yaml`

## Configuration

Create a `config/nova.yaml` file with your settings:

```yaml
# Base configuration
base_dir: ~/nova           # Base directory for all Nova operations
input_dir: ~/nova/input    # Input directory for documents
output_dir: ~/nova/output  # Output directory for processed files
processing_dir: ~/nova/tmp # Temporary processing directory

# Cache configuration
cache:
  dir: ~/nova/cache
  enabled: true
  ttl: 3600  # 1 hour

# API configuration
apis:
  openai:
    api_key: "your-api-key-here"  # Your OpenAI API key
    model: "gpt-4o"
    max_tokens: 500
```

## Usage

1. Place documents in your input directory
2. Run `./run_nova.sh` to process documents
3. Find processed files in your output directory

## Development

See [Development Guidelines](docs/development.md) for coding standards and practices.

## License

MIT License - see LICENSE file for details



