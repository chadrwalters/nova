"""Example script demonstrating Nova image processing."""
import asyncio
import logging
from pathlib import Path

from nova import Nova


async def main():
    """Process images in example directory."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize Nova with default configuration
    nova = Nova()
    
    # Create example directories
    example_dir = Path(__file__).parent
    input_dir = example_dir / "input"
    output_dir = example_dir / "output"
    
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # Log supported formats
    logger.info("Supported formats: %s", nova.get_supported_formats())
    
    # Process all supported files in input directory
    try:
        results = await nova.process_directory(input_dir, output_dir)
        logger.info("Successfully processed %d files", len(results))
        
        # Print metadata for each processed file
        for metadata in results:
            logger.info(
                "Processed %s: %s",
                metadata["file_type"],
                metadata["source_path"],
            )
            
            if metadata["images"]:
                logger.info("  Images processed: %d", len(metadata["images"]))
            
            if metadata["warnings"]:
                logger.warning("  Warnings: %s", metadata["warnings"])
            
            if metadata["errors"]:
                logger.error("  Errors: %s", metadata["errors"])
    
    except Exception as e:
        logger.error("Failed to process directory", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main()) 