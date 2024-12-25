"""Main module for Nova document processor."""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List

from .config import PipelineConfig, PathConfig, ProcessorConfig
from .logging import get_logger
from .errors import PipelineError
from .pipeline.manager import PipelineManager

logger = get_logger(__name__)

def load_environment() -> None:
    """Load environment variables."""
    try:
        logger.info("Loading environment...")
        
        # Check required environment variables
        required_vars = [
            'NOVA_BASE_DIR',
            'NOVA_INPUT_DIR',
            'NOVA_OUTPUT_DIR',
            'NOVA_PROCESSING_DIR',
            'NOVA_TEMP_DIR',
            'NOVA_PHASE_MARKDOWN_PARSE',
            'NOVA_PHASE_MARKDOWN_CONSOLIDATE',
            'NOVA_PHASE_MARKDOWN_AGGREGATE',
            'NOVA_PHASE_MARKDOWN_SPLIT'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise PipelineError(f"Missing environment variables: {', '.join(missing_vars)}")
        
        logger.info("Environment loaded")
        
    except Exception as e:
        logger.error(f"Failed to load environment: {str(e)}")
        sys.exit(1)

def verify_directories() -> None:
    """Verify required directories exist."""
    try:
        logger.info("\nVerifying directories...")
        
        # Get required directories from environment
        base_dir = os.getenv('NOVA_BASE_DIR')
        input_dir = os.getenv('NOVA_INPUT_DIR')
        output_dir = os.getenv('NOVA_OUTPUT_DIR')
        processing_dir = os.getenv('NOVA_PROCESSING_DIR')
        temp_dir = os.getenv('NOVA_TEMP_DIR')
        
        # Create directories if they don't exist
        for dir_path in [base_dir, input_dir, output_dir, processing_dir, temp_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        
    except Exception as e:
        logger.error(f"Failed to verify directories: {str(e)}")
        sys.exit(1)

def create_phase_directories() -> None:
    """Create phase output directories."""
    try:
        logger.info("\nCreating Phase 1 Output Directories...")
        
        # Get phase directories from environment
        phase_dirs = [
            os.getenv('NOVA_PHASE_MARKDOWN_PARSE'),
            os.getenv('NOVA_PHASE_MARKDOWN_CONSOLIDATE'),
            os.getenv('NOVA_PHASE_MARKDOWN_AGGREGATE'),
            os.getenv('NOVA_PHASE_MARKDOWN_SPLIT')
        ]
        
        # Create directories if they don't exist
        for dir_path in phase_dirs:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        
    except Exception as e:
        logger.error(f"Failed to create phase directories: {str(e)}")
        sys.exit(1)

def check_poetry_installation() -> None:
    """Check if Poetry is installed."""
    try:
        logger.info("\nChecking Poetry installation...")
        
        # Check if poetry is installed
        if os.system("poetry --version > /dev/null 2>&1") != 0:
            raise PipelineError("Poetry is not installed")
        
        logger.info("Poetry is installed")
        
    except Exception as e:
        logger.error(f"Failed to check Poetry installation: {str(e)}")
        sys.exit(1)

def check_input_files() -> None:
    """Check for input files."""
    try:
        logger.info("\nChecking input files...")
        
        # Get input directory from environment
        input_dir = os.getenv('NOVA_INPUT_DIR')
        
        # Count markdown files
        markdown_files = list(Path(input_dir).glob('**/*.md'))
        file_count = len(markdown_files)
        
        if file_count == 0:
            raise PipelineError("No markdown files found in input directory")
        
        logger.info(f"Found {file_count:>8} markdown files")
        
    except Exception as e:
        logger.error(f"Failed to check input files: {str(e)}")
        sys.exit(1)

async def process(
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
    start_phase: Optional[str] = None,
    end_phase: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None
) -> bool:
    """Process documents.
    
    Args:
        input_path: Optional input path (defaults to NOVA_INPUT_DIR)
        output_path: Optional output path (defaults to NOVA_OUTPUT_DIR)
        start_phase: Optional phase to start from
        end_phase: Optional phase to end at
        options: Optional processing options
        
    Returns:
        True if processing completed successfully
    """
    try:
        logger.info("\nRunning pipeline...")
        
        # Get paths from environment if not provided
        input_path = input_path or os.getenv('NOVA_INPUT_DIR')
        output_path = output_path or os.getenv('NOVA_OUTPUT_DIR')
        
        # Create pipeline configuration
        config = PipelineConfig(
            paths=PathConfig(base_dir=Path(os.getenv('NOVA_BASE_DIR'))),
            phases=[
                'MARKDOWN_PARSE',
                'MARKDOWN_CONSOLIDATE',
                'MARKDOWN_AGGREGATE',
                'MARKDOWN_SPLIT_THREEFILES'
            ]
        )
        
        # Create processor configurations
        split_config = ProcessorConfig(
            output_dir=Path(os.getenv('NOVA_PHASE_MARKDOWN_SPLIT')),
            options={
                'components': {
                    'three_file_split_processor': {
                        'config': {
                            'output_files': {
                                'summary': 'summary.md',
                                'raw_notes': 'raw_notes.md',
                                'attachments': 'attachments.md'
                            },
                            'section_markers': {
                                'summary': '--==SUMMARY==--',
                                'raw_notes': '--==RAW NOTES==--',
                                'attachments': '--==ATTACHMENTS==--'
                            },
                            'attachment_markers': {
                                'start': '--==ATTACHMENT_BLOCK: {filename}==--',
                                'end': '--==ATTACHMENT_BLOCK_END==--'
                            },
                            'content_type_rules': {
                                'summary': [
                                    'Contains high-level overviews',
                                    'Contains key insights and decisions',
                                    'Contains structured content'
                                ],
                                'raw_notes': [
                                    'Contains detailed notes and logs',
                                    'Contains chronological entries',
                                    'Contains unstructured content'
                                ],
                                'attachments': [
                                    'Contains file references',
                                    'Contains embedded content',
                                    'Contains metadata'
                                ]
                            },
                            'content_preservation': {
                                'validate_input_size': True,
                                'validate_output_size': True,
                                'track_content_markers': True,
                                'verify_section_integrity': True
                            },
                            'cross_linking': True,
                            'preserve_headers': True
                        }
                    }
                }
            }
        )
        
        # Create pipeline manager
        pipeline = PipelineManager(config)
        
        # Register processors
        from ..phases.parse.processor import ParseProcessor
        from ..phases.consolidate.processor import ConsolidateProcessor
        from ..phases.aggregate.processor import AggregateProcessor
        from ..phases.split.processor import ThreeFileSplitProcessor
        
        pipeline.register_processor('MARKDOWN_PARSE', ParseProcessor(
            ProcessorConfig(output_dir=Path(os.getenv('NOVA_PHASE_MARKDOWN_PARSE'))),
            config
        ))
        pipeline.register_processor('MARKDOWN_CONSOLIDATE', ConsolidateProcessor(
            ProcessorConfig(output_dir=Path(os.getenv('NOVA_PHASE_MARKDOWN_CONSOLIDATE'))),
            config
        ))
        pipeline.register_processor('MARKDOWN_AGGREGATE', AggregateProcessor(
            ProcessorConfig(output_dir=Path(os.getenv('NOVA_PHASE_MARKDOWN_AGGREGATE'))),
            config
        ))
        pipeline.register_processor('MARKDOWN_SPLIT_THREEFILES', ThreeFileSplitProcessor(
            split_config,
            config
        ))
        
        # Run pipeline
        success = await pipeline.run_pipeline(
            input_path=input_path,
            output_path=output_path,
            start_phase=start_phase,
            end_phase=end_phase,
            options=options
        )
        
        if success:
            logger.info("\nPipeline completed successfully")
            logger.info(f"\nOutput files are in: {output_path}")
        else:
            logger.error("\nPipeline failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to process documents: {str(e)}")
        return False

def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Nova document processor')
    parser.add_argument('command', choices=['process'], help='Command to execute')
    parser.add_argument('--input-dir', help='Input directory', default=os.getenv('NOVA_INPUT_DIR'))
    parser.add_argument('--output-dir', help='Output directory', default=os.getenv('NOVA_OUTPUT_DIR'))
    parser.add_argument('--force', '-f', action='store_true', help='Force processing')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Show what would be done')
    parser.add_argument('--show-state', '-s', action='store_true', help='Display current state')
    parser.add_argument('--scan', action='store_true', help='Show directory structure')
    
    return parser.parse_args()

def cli() -> int:
    """Command line interface entry point.
    
    Returns:
        Exit code
    """
    args = parse_args()
    
    if args.command == 'process':
        # Load environment
        load_environment()
        
        # Verify directories
        verify_directories()
        
        # Create phase directories
        create_phase_directories()
        
        # Check Poetry installation
        check_poetry_installation()
        
        # Check input files
        check_input_files()
        
        # Run pipeline
        if os.name == 'posix':
            asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        else:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(process(
                input_path=args.input_dir,
                output_path=args.output_dir,
                options={
                    'force': args.force,
                    'dry_run': args.dry_run,
                    'show_state': args.show_state,
                    'scan': args.scan
                }
            ))
            if not success:
                return 1
        finally:
            loop.close()
        
        return 0
    
    return 0

async def main():
    try:
        # Create pipeline configuration
        config = PipelineConfig(
            paths=PathConfig(base_dir=Path(os.getenv('NOVA_BASE_DIR'))),
            phases=[
                'MARKDOWN_PARSE',
                'MARKDOWN_CONSOLIDATE',
                'MARKDOWN_AGGREGATE',
                'MARKDOWN_SPLIT_THREEFILES'
            ]
        )
        
        # Create processor configurations
        split_config = ProcessorConfig(
            output_dir=Path(os.getenv('NOVA_PHASE_MARKDOWN_SPLIT')),
            options={
                'components': {
                    'three_file_split_processor': {
                        'config': {
                            'output_files': {
                                'summary': 'summary.md',
                                'raw_notes': 'raw_notes.md',
                                'attachments': 'attachments.md'
                            },
                            'section_markers': {
                                'summary': '--==SUMMARY==--',
                                'raw_notes': '--==RAW NOTES==--',
                                'attachments': '--==ATTACHMENTS==--'
                            },
                            'attachment_markers': {
                                'start': '--==ATTACHMENT_BLOCK: {filename}==--',
                                'end': '--==ATTACHMENT_BLOCK_END==--'
                            },
                            'content_type_rules': {
                                'summary': [
                                    'Contains high-level overviews',
                                    'Contains key insights and decisions',
                                    'Contains structured content'
                                ],
                                'raw_notes': [
                                    'Contains detailed notes and logs',
                                    'Contains chronological entries',
                                    'Contains unstructured content'
                                ],
                                'attachments': [
                                    'Contains file references',
                                    'Contains embedded content',
                                    'Contains metadata'
                                ]
                            },
                            'content_preservation': {
                                'validate_input_size': True,
                                'validate_output_size': True,
                                'track_content_markers': True,
                                'verify_section_integrity': True
                            },
                            'cross_linking': True,
                            'preserve_headers': True
                        }
                    }
                }
            }
        )
        
        # Create pipeline manager
        pipeline = PipelineManager(config)
        
        # Register processors
        pipeline.register_processor('MARKDOWN_PARSE', ParseProcessor(
            ProcessorConfig(output_dir=Path(os.getenv('NOVA_PHASE_MARKDOWN_PARSE'))),
            config
        ))
        pipeline.register_processor('MARKDOWN_CONSOLIDATE', ConsolidateProcessor(
            ProcessorConfig(output_dir=Path(os.getenv('NOVA_PHASE_MARKDOWN_CONSOLIDATE'))),
            config
        ))
        pipeline.register_processor('MARKDOWN_AGGREGATE', AggregateProcessor(
            ProcessorConfig(output_dir=Path(os.getenv('NOVA_PHASE_MARKDOWN_AGGREGATE'))),
            config
        ))
        pipeline.register_processor('MARKDOWN_SPLIT_THREEFILES', ThreeFileSplitProcessor(
            split_config,
            config
        ))
        
        # Run pipeline
        success = await pipeline.run()
        if not success:
            raise Exception("Pipeline failed")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 