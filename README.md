# Nova Document Processor

A powerful document processing pipeline for managing and transforming markdown files and their attachments.

## Documentation

- [Configuration System](docs/configuration.md): Details about the configuration system and how to modify it
- [Pipeline Schema](docs/schema.md): Pipeline configuration schema and validation rules

## Installation

1. Clone the repository
2. Run `./install.sh` to set up the environment
3. Copy `.env.template` to `.env` and configure your environment variables

## Usage

Run the pipeline:
```bash
./consolidate.sh
```

This will:
1. Process markdown files from the input directory
2. Convert and optimize images
3. Extract content from office documents
4. Generate a consolidated output

## Configuration

Nova uses a split configuration system:
1. `config/default_config.yaml`: Global system configuration
2. `config/pipeline.yaml`: Pipeline-specific configuration

See the [Configuration Documentation](docs/configuration.md) for details.

## Development

1. Install development dependencies:
```bash
poetry install --with dev
```

2. Run tests:
```bash
./run_tests.sh
```

## License

MIT License 