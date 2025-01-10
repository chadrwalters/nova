import argparse
from pathlib import Path

from nova.utils.config import NovaConfig


def main():
    parser = argparse.ArgumentParser(description="Nova - Personal Knowledge Management System")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/nova.yaml"),
        help="Path to configuration file",
    )
    args = parser.parse_args()

    try:
        config = NovaConfig.from_yaml(args.config)
        print("Configuration loaded successfully:")
        print(f"Debug mode: {config.debug}")
        print(f"Log level: {config.log_level}")
        print(f"Chunk size: {config.ingestion.chunk_size}")
        return 0
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 