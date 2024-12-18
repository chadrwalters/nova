from pathlib import Path
from typing import List, Optional
import structlog
import json
import shutil
import asyncio
import aiofiles
from .config import NovaConfig
from .processor import process_markdown_file
from .docx_processor import WordProcessor
from .errors import ErrorHandler, ProcessingError, ErrorSeverity
from .logging import get_logger

logger = get_logger(__name__)

class Pipeline:
    """Document processing pipeline."""
    
    def __init__(self, config: NovaConfig):
        self.config = config
        self.error_handler = ErrorHandler()
        self.assets_dir = Path(config.document_handling.word_processing["image_output_dir"])
        
    async def process(self, input_path: Path, output_path: Path) -> bool:
        """Process markdown files through the pipeline."""
        try:
            # Validate input
            if not input_path.exists():
                logger.error("input_not_found", path=str(input_path))
                return False
            
            # Handle directory input
            if input_path.is_dir():
                success = True
                tasks = []
                for file in input_path.glob("*.md"):
                    logger.info("processing_file", file=str(file))
                    tasks.append(process_markdown_file(file, output_path, self.config))
                
                # Process files concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check results
                for file, result in zip(input_path.glob("*.md"), results):
                    if isinstance(result, Exception):
                        logger.error("file_processing_failed",
                                   file=str(file),
                                   error=str(result))
                        success = False
                    elif not result:
                        success = False
                        
                return success
            
            # Process single file
            result = await process_markdown_file(input_path, output_path, self.config)
            
            return result
            
        except Exception as e:
            self.error_handler.add_error(ProcessingError(
                message=f"Pipeline processing failed: {str(e)}",
                severity=ErrorSeverity.ERROR,
                source="Pipeline.process",
                details={"input": str(input_path), "output": str(output_path)}
            ))
            logger.error("pipeline_failed",
                        error=str(e),
                        input=str(input_path),
                        output=str(output_path))
            return False
            
    async def consolidate(self, input_path: Path, output_path: Path) -> bool:
        """Consolidate processed markdown files."""
        try:
            # Validate input
            if not input_path.exists():
                logger.error("input_not_found", path=str(input_path))
                return False
                
            # Create output directory if it doesn't exist
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Get all markdown files
            markdown_files = sorted(input_path.glob("*.md"))
            if not markdown_files:
                logger.error("no_markdown_files", path=str(input_path))
                return False
                
            # Initialize consolidated content
            consolidated = []
            metadata = {}
            
            # Process each file
            for file in markdown_files:
                try:
                    # Read file content
                    async with aiofiles.open(file, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        
                    # Read metadata if exists
                    meta_file = file.with_suffix('.md.meta.json')
                    if meta_file.exists():
                        async with aiofiles.open(meta_file, 'r', encoding='utf-8') as f:
                            file_meta = json.loads(await f.read())
                            metadata[file.name] = file_meta
                            
                    # Add file separator if not first file
                    if consolidated:
                        consolidated.append("\n\n---\n\n")
                        
                    # Add file content
                    consolidated.append(content)
                    
                except Exception as e:
                    logger.error("file_consolidation_failed",
                               file=str(file),
                               error=str(e))
                    return False
                    
            # Write consolidated content
            output_file = output_path / "consolidated.md"
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write("\n".join(consolidated))
                
            # Write consolidated metadata
            meta_file = output_file.with_suffix('.md.meta.json')
            async with aiofiles.open(meta_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(metadata, indent=2) + '\n')
                
            logger.info("consolidation_complete",
                       input=str(input_path),
                       output=str(output_file))
            return True
            
        except Exception as e:
            self.error_handler.add_error(ProcessingError(
                message=f"Consolidation failed: {str(e)}",
                severity=ErrorSeverity.ERROR,
                source="Pipeline.consolidate",
                details={"input": str(input_path), "output": str(output_path)}
            ))
            logger.error("consolidation_failed",
                        error=str(e),
                        input=str(input_path),
                        output=str(output_path))
            return False

def setup_environment(config_path: Optional[Path] = None) -> NovaConfig:
    """Set up processing environment and load configuration."""
    try:
        # Load config
        config = load_config(config_path)
        
        # Convert all path configs to Path objects
        config.processing.input_dir = Path(str(config.processing.input_dir))
        config.processing.processing_dir = Path(str(config.processing.processing_dir))
        config.processing.phase_markdown_parse = Path(str(config.processing.phase_markdown_parse))
        config.processing.phase_markdown_consolidate = Path(str(config.processing.phase_markdown_consolidate))
        config.processing.phase_pdf_generate = Path(str(config.processing.phase_pdf_generate))
        config.processing.temp_dir = Path(str(config.processing.temp_dir))
        
        # Create required directories
        config.processing.processing_dir.mkdir(parents=True, exist_ok=True)
        config.processing.phase_markdown_parse.mkdir(parents=True, exist_ok=True)
        config.processing.phase_markdown_consolidate.mkdir(parents=True, exist_ok=True)
        config.processing.phase_pdf_generate.mkdir(parents=True, exist_ok=True)
        config.processing.temp_dir.mkdir(parents=True, exist_ok=True)
        
        return config
        
    except Exception as e:
        logger.error("environment_setup_failed", error=str(e))
        raise