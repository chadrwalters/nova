"""Core Nova document processing system."""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from nova.config.manager import ConfigManager
from nova.handlers.registry import HandlerRegistry


class Nova:
    """Main Nova document processing system."""
    
    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        create_dirs: bool = True,
    ) -> None:
        """Initialize Nova system.
        
        Args:
            config_path: Path to configuration file. If not provided, will check
                environment variable NOVA_CONFIG_PATH, then fall back to default.
            create_dirs: Whether to create configured directories if they don't exist.
        """
        self.config = ConfigManager(config_path, create_dirs)
        self.handlers = HandlerRegistry(self.config)
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logging for Nova system.
        
        Returns:
            Configured logger instance.
        """
        logger = logging.getLogger("nova")
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        
        # Create file handler
        log_dir = self.config.base_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"nova_{datetime.now():%Y%m%d}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatters
        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # Add formatters to handlers
        console.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)
        
        # Add handlers to logger
        logger.addHandler(console)
        logger.addHandler(file_handler)
        
        return logger
    
    def _save_metadata(self, metadata: Dict, output_dir: Path) -> None:
        """Save metadata to file.
        
        Args:
            metadata: Metadata to save.
            output_dir: Output directory.
        """
        try:
            # Get relative path from input dir to maintain directory structure
            rel_path = Path(metadata['file_path']).relative_to(self.config.input_dir)
            metadata_dir = output_dir / rel_path.parent
            metadata_dir.mkdir(parents=True, exist_ok=True)
            
            # Save metadata
            metadata_file = metadata_dir / f"{rel_path.stem}_metadata.json"
            with open(metadata_file, "w", encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {str(e)}")
            
    def _safe_path(self, path: Union[str, Path]) -> Path:
        """Convert path to Path object safely.
        
        Args:
            path: Path to convert.
            
        Returns:
            Path object.
        """
        if path is None:
            return None
            
        try:
            # If already a Path, convert to string first
            path_str = str(path)
            
            # Handle Windows encoding
            safe_str = path_str.encode('cp1252', errors='replace').decode('cp1252')
            
            # Convert back to Path
            return Path(safe_str)
        except Exception:
            # If all else fails, use the path as is
            return Path(path)
    
    async def process_file(
        self,
        file_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Optional[Dict]:
        """Process single file.
        
        Args:
            file_path: Path to file to process.
            output_dir: Optional output directory. If not provided,
                will use configured output directory.
        
        Returns:
            Metadata about processed document, or None if file was skipped.
        """
        # Convert paths safely
        file_path = self._safe_path(file_path)
        output_dir = self._safe_path(output_dir) if output_dir else None
        
        self.logger.info(f"Processing file: {file_path}")
        
        try:
            # Process file with appropriate handler
            metadata = await self.handlers.process_file(file_path, output_dir)
            
            # Skip if no handler processed the file
            if metadata is None:
                self.logger.debug(f"No handler found for file: {file_path}")
                return None
            
            # Save metadata
            output_dir = self._safe_path(output_dir or self.config.output_dir)
            self._save_metadata(metadata.to_dict(), output_dir)
            
            # Log success or warning based on processing status
            if metadata.processed:
                self.logger.info(f"Successfully processed file: {file_path}")
            else:
                self.logger.warning(f"File processed with warnings: {file_path}")
                if metadata.errors:
                    for error in metadata.errors:
                        self.logger.warning(f"  - {error}")
            
            return metadata.to_dict()
            
        except Exception as e:
            self.logger.error(f"Failed to process file: {file_path}", exc_info=True)
            return None
    
    async def process_directory(
        self,
        input_dir: Optional[Union[str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
        recursive: bool = True,
    ) -> List[Dict]:
        """Process all files in directory.
        
        Args:
            input_dir: Input directory. If not provided,
                will use configured input directory.
            output_dir: Output directory. If not provided,
                will use configured output directory.
            recursive: Whether to process subdirectories.
            
        Returns:
            List of metadata about processed documents.
        """
        # Convert paths safely
        input_dir = self._safe_path(input_dir or self.config.input_dir)
        output_dir = self._safe_path(output_dir or self.config.output_dir)
        
        self.logger.info(f"Processing directory: {input_dir}")
        
        results = []
        errors = []
        pattern = "**/*" if recursive else "*"
        
        try:
            for file_path in input_dir.glob(pattern):
                if file_path.is_file():
                    try:
                        metadata = await self.process_file(file_path, output_dir)
                        if metadata is not None:
                            results.append(metadata)
                    except Exception as e:
                        self.logger.error(f"Error processing {file_path}: {str(e)}")
                        errors.append(str(file_path))
                        continue
            
            self.logger.info(f"Processed {len(results)} files")
            if errors:
                self.logger.warning(f"Failed to process {len(errors)} files")
                for error_file in errors:
                    self.logger.warning(f"  - {error_file}")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to process directory: {input_dir}", exc_info=True)
            raise
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats.
        
        Returns:
            List of supported file extensions.
        """
        return self.handlers.get_supported_formats() 