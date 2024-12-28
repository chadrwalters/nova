"""Consolidate markdown files with their attachments."""

import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from ..core import (
    PipelineManager,
    get_logger,
    setup_logging,
    load_config
)


# Initialize logging
logger = get_logger(__name__)
console = Console()


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
    default="config/pipeline_config.yaml"
)
@click.option(
    "--base-dir",
    "-b",
    type=click.Path(exists=True),
    help="Base directory for operations"
)
@click.option(
    "--input-dir",
    "-i",
    type=click.Path(exists=True),
    help="Input directory containing markdown files"
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    help="Output directory for consolidated files"
)
@click.option(
    "--temp-dir",
    "-t",
    type=click.Path(),
    help="Temporary directory for processing"
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="Logging level"
)
def main(
    config: Optional[str] = None,
    base_dir: Optional[str] = None,
    input_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    temp_dir: Optional[str] = None,
    log_level: str = "INFO"
) -> None:
    """Consolidate markdown files with their attachments."""
    try:
        # Set up logging
        setup_logging(level=log_level)
        
        # Print environment info
        print("Validating environment variables...")
        print("Using directories:")
        print(f"Base dir: {base_dir or os.getenv('NOVA_BASE_DIR')}")
        print(f"Input dir: {input_dir or os.getenv('NOVA_INPUT_DIR')}")
        print(f"Processing dir: {os.getenv('NOVA_PROCESSING_DIR')}")
        print(f"Parse dir: {os.getenv('NOVA_PHASE_MARKDOWN_PARSE')}")
        
        # Create required directories
        print("Creating required directories...")
        for env_var in [
            "NOVA_PHASE_MARKDOWN_PARSE",
            "NOVA_PHASE_MARKDOWN_CONSOLIDATE",
            "NOVA_PHASE_MARKDOWN_AGGREGATE",
            "NOVA_PHASE_MARKDOWN_SPLIT"
        ]:
            dir_path = os.getenv(env_var)
            if dir_path:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                
        print("Verifying directories...")
        
        # Load configuration
        if config and Path(config).exists():
            logger.info(f"Loading configuration from {config}")
            pipeline_config = load_config(config)
        else:
            logger.warning(f"Configuration file not found: {config}")
            logger.info("Using default configuration")
            # Use environment variables or defaults
            pipeline_config = {
                "pipeline": {
                    "paths": {
                        "base_dir": base_dir or os.getenv("NOVA_BASE_DIR"),
                        "input_dir": input_dir or os.getenv("NOVA_INPUT_DIR"),
                        "output_dir": output_dir or os.getenv("NOVA_OUTPUT_DIR"),
                        "temp_dir": temp_dir or os.getenv("NOVA_TEMP_DIR")
                    },
                    "phases": {
                        "markdown_parse": {
                            "description": "Parse and process markdown files with embedded content",
                            "output_dir": os.getenv("NOVA_PHASE_MARKDOWN_PARSE"),
                            "processor": "MarkdownProcessor",
                            "enabled": True,
                            "handlers": [
                                {
                                    "type": "UnifiedHandler",
                                    "base_handler": "nova.phases.core.base_handler.BaseHandler",
                                    "options": {
                                        "document_conversion": True,
                                        "image_processing": True,
                                        "metadata_preservation": True,
                                        "sort_by_date": True,
                                        "preserve_headers": True,
                                        "section_markers": {
                                            "start": "<!-- START_FILE: {filename} -->",
                                            "end": "<!-- END_FILE: {filename} -->",
                                            "separator": "\n---\n"
                                        }
                                    }
                                }
                            ]
                        },
                        "markdown_consolidate": {
                            "description": "Consolidate markdown files with their attachments",
                            "output_dir": os.getenv("NOVA_PHASE_MARKDOWN_CONSOLIDATE"),
                            "processor": "MarkdownConsolidateProcessor",
                            "enabled": True,
                            "handlers": [
                                {
                                    "type": "UnifiedHandler",
                                    "base_handler": "nova.phases.core.base_handler.BaseHandler",
                                    "options": {
                                        "copy_attachments": True,
                                        "update_references": True,
                                        "merge_content": True,
                                        "preserve_headers": True,
                                        "sort_by_date": True
                                    }
                                }
                            ]
                        },
                        "markdown_aggregate": {
                            "description": "Aggregate all consolidated markdown files into a single file",
                            "output_dir": os.getenv("NOVA_PHASE_MARKDOWN_AGGREGATE"),
                            "processor": "MarkdownAggregateProcessor",
                            "enabled": True,
                            "handlers": [
                                {
                                    "type": "UnifiedHandler",
                                    "base_handler": "nova.phases.core.base_handler.BaseHandler",
                                    "options": {
                                        "section_markers": {
                                            "start": "<!-- START_FILE: {filename} -->",
                                            "end": "<!-- END_FILE: {filename} -->",
                                            "separator": "\n---\n"
                                        },
                                        "sort_by_date": True,
                                        "preserve_headers": True,
                                        "add_navigation": True,
                                        "link_style": "text",
                                        "templates": {
                                            "text": {
                                                "prev": "← Previous: [{title}]({link})",
                                                "next": "Next: [{title}]({link}) →",
                                                "top": "[↑ Back to Top](#table-of-contents)"
                                            }
                                        }
                                    }
                                }
                            ]
                        },
                        "markdown_split": {
                            "description": "Split aggregated markdown into separate files",
                            "output_dir": os.getenv("NOVA_PHASE_MARKDOWN_SPLIT"),
                            "processor": "SplitProcessor",
                            "enabled": True,
                            "handlers": [
                                {
                                    "type": "UnifiedHandler",
                                    "base_handler": "nova.phases.core.base_handler.BaseHandler",
                                    "options": {
                                        "output_files": {
                                            "summary": "summary.md",
                                            "raw_notes": "raw_notes.md",
                                            "attachments": "attachments.md"
                                        },
                                        "section_markers": {
                                            "summary": "--==SUMMARY==--",
                                            "raw_notes": "--==RAW NOTES==--",
                                            "attachments": "--==ATTACHMENTS==--"
                                        },
                                        "attachment_markers": {
                                            "start": "--==ATTACHMENT_BLOCK: {filename}==--",
                                            "end": "--==ATTACHMENT_BLOCK_END==--"
                                        },
                                        "content_preservation": {
                                            "validate_input_size": True,
                                            "validate_output_size": True,
                                            "track_content_markers": True,
                                            "verify_section_integrity": True
                                        },
                                        "cross_linking": True,
                                        "preserve_headers": True
                                    }
                                }
                            ]
                        }
                    }
                }
            }
            
        print("Running consolidation pipeline...")
        
        # Create pipeline manager
        pipeline = PipelineManager(
            config=pipeline_config,
            console=console
        )
        
        # Run pipeline
        if not pipeline.run():
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
        

if __name__ == "__main__":
    main() 