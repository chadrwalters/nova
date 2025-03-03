"""
Upload Markdown command handler.

This module provides the command handler for the upload-markdown command.
"""

from pathlib import Path
from typing import List

from nova.config import MainConfig, load_config
from nova.exceptions import ConfigurationError, GraphlitClientError, UploadError
from nova.utils import get_logger

logger = get_logger(__name__)


async def upload_markdown_command(
    config_path: str, output_dir: str, dry_run: bool
) -> None:
    """
    Upload Markdown files from the output directory to Graphlit.

    Args:
        config_path: Path to the Graphlit configuration file.
        output_dir: Directory containing Markdown files to upload.
        dry_run: If True, list files to upload without uploading.

    Raises:
        ConfigurationError: If the configuration is invalid.
        UploadError: If an error occurs during upload.
    """
    logger.info(f"Loading configuration from {config_path}")

    try:
        # Load and validate configuration
        config_path = Path(config_path).resolve()
        config = load_config(str(config_path), MainConfig)

        # Log configuration details (excluding sensitive information)
        logger.info(
            f"Configuration loaded successfully: "
            f"organization_id={config.graphlit.organization_id}, "
            f"environment_id={config.graphlit.environment_id}"
        )

        # Initialize Graphlit client with validated configuration
        try:
            # Import here to avoid circular imports
            from graphlit import Graphlit

            logger.info("Initializing Graphlit client")
            graphlit = Graphlit(
                organization_id=config.graphlit.organization_id,
                environment_id=config.graphlit.environment_id,
                jwt_secret=config.graphlit.jwt_secret,
            )
        except ImportError as e:
            logger.error("Failed to import Graphlit client library")
            raise UploadError(
                "Graphlit client library not found. "
                "Install with: uv pip install graphlit-client"
            ) from e
        except Exception as e:
            logger.error(f"Error initializing Graphlit client: {e}")
            raise GraphlitClientError(f"Error initializing Graphlit client: {e}") from e

        # Validate output directory
        output_path = Path(output_dir).resolve()
        if not output_path.exists():
            logger.error(f"Output directory not found: {output_path}")
            raise UploadError(f"Output directory not found: {output_path}")
        if not output_path.is_dir():
            logger.error(f"Not a directory: {output_path}")
            raise UploadError(f"Not a directory: {output_path}")

        # Find all Markdown files in the output directory
        markdown_files: List[Path] = list(output_path.glob("**/*.md"))

        if not markdown_files:
            logger.warning(f"No Markdown files found in {output_path}")
            return

        # Handle dry run
        if dry_run:
            logger.info(
                "Dry run: Listing Markdown files to be uploaded (but not uploading):"
            )
            for md_file in markdown_files:
                logger.info(f"  - {md_file.relative_to(output_path)}")
            return

        # Upload files
        logger.info(f"Uploading {len(markdown_files)} Markdown files to Graphlit...")

        for md_file in markdown_files:
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    file_content = f.read()

                file_name = md_file.name
                relative_path = md_file.relative_to(output_path)

                logger.info(f"Uploading {relative_path}")
                response = await graphlit.client.ingest_text(
                    name=file_name, text=file_content, is_synchronous=True
                )

                if (
                    response
                    and hasattr(response, "ingest_text")
                    and response.ingest_text
                ):
                    content_id = response.ingest_text.id
                    logger.info(f"Uploaded {relative_path} (Content ID: {content_id})")
                else:
                    logger.error(f"Failed to upload {relative_path}")
                    raise UploadError(
                        f"Failed to upload {relative_path}",
                        file_path=str(md_file),
                    )
            except Exception as e:
                logger.error(f"Error uploading {md_file.relative_to(output_path)}: {e}")
                raise UploadError(
                    f"Error uploading {md_file.relative_to(output_path)}: {e}",
                    file_path=str(md_file),
                ) from e

        logger.info("Markdown upload complete")

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {config_path}")
        raise ConfigurationError(
            f"Configuration file not found: {config_path}",
            config_file=str(config_path),
        ) from e
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        raise ConfigurationError(
            f"Invalid configuration: {e}",
            config_file=str(config_path),
        ) from e
