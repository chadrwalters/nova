#!/usr/bin/env python3

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum, auto
from markdown_processor import MarkdownProcessor
from consolidate_processor import ConsolidateProcessor
from aggregate_processor import AggregateProcessor
from markdown_splitter import MarkdownSplitter

class PipelinePhase(Enum):
    MARKDOWN_PARSE = auto()
    MARKDOWN_CONSOLIDATE = auto()
    MARKDOWN_AGGREGATE = auto()
    MARKDOWN_SPLIT_THREEFILES = auto()

class PipelineManager:
    """Manages the document processing pipeline flow."""
    
    def __init__(self):
        # Set up environment paths
        self.base_dir = Path(os.getenv("NOVA_BASE_DIR", ""))
        self.input_dir = Path(os.getenv("NOVA_INPUT_DIR", ""))
        self.output_dir = Path(os.getenv("NOVA_OUTPUT_DIR", ""))
        self.processing_dir = Path(os.getenv("NOVA_PROCESSING_DIR", ""))
        self.temp_dir = Path(os.getenv("NOVA_TEMP_DIR", ""))
        
        # Phase-specific directories
        self.phase_dirs = {
            PipelinePhase.MARKDOWN_PARSE: Path(os.getenv("NOVA_PHASE_MARKDOWN_PARSE", "")),
            PipelinePhase.MARKDOWN_CONSOLIDATE: Path(os.getenv("NOVA_PHASE_MARKDOWN_CONSOLIDATE", "")),
            PipelinePhase.MARKDOWN_AGGREGATE: Path(os.getenv("NOVA_PHASE_MARKDOWN_AGGREGATE", "")),
            PipelinePhase.MARKDOWN_SPLIT_THREEFILES: Path(os.getenv("NOVA_PHASE_MARKDOWN_SPLIT", ""))
        }
        
        # Validate environment
        self._validate_environment()
        
        # Create directories
        self._ensure_directories()
        
        # Set up logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up logging configuration."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler
        log_file = self.processing_dir / "pipeline.log"
        fh = logging.FileHandler(str(log_file))
        fh.setLevel(logging.DEBUG)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def _validate_environment(self):
        """Validate that all required environment variables are set."""
        required_vars = {
            "NOVA_BASE_DIR": self.base_dir,
            "NOVA_INPUT_DIR": self.input_dir,
            "NOVA_OUTPUT_DIR": self.output_dir,
            "NOVA_PROCESSING_DIR": self.processing_dir,
            "NOVA_TEMP_DIR": self.temp_dir,
            "NOVA_PHASE_MARKDOWN_PARSE": self.phase_dirs[PipelinePhase.MARKDOWN_PARSE],
            "NOVA_PHASE_MARKDOWN_CONSOLIDATE": self.phase_dirs[PipelinePhase.MARKDOWN_CONSOLIDATE],
            "NOVA_PHASE_MARKDOWN_AGGREGATE": self.phase_dirs[PipelinePhase.MARKDOWN_AGGREGATE],
            "NOVA_PHASE_MARKDOWN_SPLIT": self.phase_dirs[PipelinePhase.MARKDOWN_SPLIT_THREEFILES]
        }
        
        missing_vars = [
            var_name for var_name, path in required_vars.items()
            if not os.getenv(var_name) or str(path) == "."
        ]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        for dir_path in [
            self.base_dir,
            self.input_dir,
            self.output_dir,
            self.processing_dir,
            self.temp_dir,
            *self.phase_dirs.values()
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def process_phase(self, phase: PipelinePhase, options: Optional[Dict[str, Any]] = None) -> bool:
        """Process a specific pipeline phase."""
        if not isinstance(phase, PipelinePhase):
            raise ValueError(f"Invalid phase type: {type(phase)}")
        
        self.logger.info(f"Starting phase: {phase.name}")
        
        try:
            if phase == PipelinePhase.MARKDOWN_PARSE:
                return self._process_markdown_parse(options)
            elif phase == PipelinePhase.MARKDOWN_CONSOLIDATE:
                return self._process_markdown_consolidate(options)
            elif phase == PipelinePhase.MARKDOWN_AGGREGATE:
                return self._process_markdown_aggregate(options)
            elif phase == PipelinePhase.MARKDOWN_SPLIT_THREEFILES:
                return self._process_markdown_split(options)
            else:
                self.logger.error(f"Unknown phase: {phase.name}")
                return False
        except Exception as e:
            self.logger.error(f"Error in phase {phase.name}: {str(e)}")
            return False
    
    def _process_markdown_parse(self, options: Optional[Dict[str, Any]] = None) -> bool:
        """Process the MARKDOWN_PARSE phase."""
        self.logger.info("Processing markdown parse phase")
        
        try:
            # Create markdown processor
            processor = MarkdownProcessor(
                input_dir=self.input_dir,
                output_dir=self.phase_dirs[PipelinePhase.MARKDOWN_PARSE],
                temp_dir=self.temp_dir
            )
            
            # Process all markdown files
            success = processor.process_directory()
            
            if success:
                self.logger.info("Markdown parse phase completed successfully")
            else:
                self.logger.error("Markdown parse phase failed")
            
            return success
        
        except Exception as e:
            self.logger.error(f"Error in markdown parse phase: {str(e)}")
            return False
    
    def _process_markdown_consolidate(self, options: Optional[Dict[str, Any]] = None) -> bool:
        """Process the MARKDOWN_CONSOLIDATE phase."""
        self.logger.info("Processing markdown consolidate phase")
        
        try:
            # Create consolidate processor
            processor = ConsolidateProcessor(
                input_dir=self.phase_dirs[PipelinePhase.MARKDOWN_PARSE],
                output_dir=self.phase_dirs[PipelinePhase.MARKDOWN_CONSOLIDATE]
            )
            
            # Process all markdown files
            success = processor.process_directory()
            
            if success:
                self.logger.info("Markdown consolidate phase completed successfully")
            else:
                self.logger.error("Markdown consolidate phase failed")
            
            return success
        
        except Exception as e:
            self.logger.error(f"Error in markdown consolidate phase: {str(e)}")
            return False
    
    def _process_markdown_aggregate(self, options: Optional[Dict[str, Any]] = None) -> bool:
        """Process the MARKDOWN_AGGREGATE phase."""
        self.logger.info("Processing markdown aggregate phase")
        
        try:
            # Create aggregate processor
            processor = AggregateProcessor(
                input_dir=self.phase_dirs[PipelinePhase.MARKDOWN_CONSOLIDATE],
                output_dir=self.phase_dirs[PipelinePhase.MARKDOWN_AGGREGATE]
            )
            
            # Process all markdown files
            result = processor.process()
            
            if result:
                self.logger.info("Markdown aggregate phase completed successfully")
                return True
            else:
                self.logger.error("Markdown aggregate phase failed")
                return False
        
        except Exception as e:
            self.logger.error(f"Error in markdown aggregate phase: {str(e)}")
            return False
    
    def _process_markdown_split(self, options: Optional[Dict[str, Any]] = None) -> bool:
        """Process the MARKDOWN_SPLIT_THREEFILES phase."""
        self.logger.info("Processing markdown split phase")
        
        try:
            # Create splitter processor
            processor = MarkdownSplitter(
                input_dir=self.phase_dirs[PipelinePhase.MARKDOWN_AGGREGATE],
                output_dir=self.phase_dirs[PipelinePhase.MARKDOWN_SPLIT_THREEFILES]
            )
            
            # Process the aggregated file
            result = processor.process()
            
            if result:
                self.logger.info("Markdown split phase completed successfully")
                return True
            else:
                self.logger.error("Markdown split phase failed")
                return False
        
        except Exception as e:
            self.logger.error(f"Error in markdown split phase: {str(e)}")
            return False
    
    def run_pipeline(self, start_phase: Optional[PipelinePhase] = None, 
                    end_phase: Optional[PipelinePhase] = None,
                    options: Optional[Dict[str, Any]] = None) -> bool:
        """Run the complete pipeline or a subset of phases."""
        phases = list(PipelinePhase)
        if start_phase:
            start_idx = phases.index(start_phase)
            phases = phases[start_idx:]
        if end_phase:
            end_idx = phases.index(end_phase) + 1
            phases = phases[:end_idx]
        
        success = True
        for phase in phases:
            self.logger.info(f"=== Starting Phase: {phase.name} ===")
            phase_success = self.process_phase(phase, options)
            if not phase_success:
                self.logger.error(f"Pipeline failed at phase: {phase.name}")
                success = False
                break
            self.logger.info(f"=== Completed Phase: {phase.name} ===")
        
        return success

if __name__ == "__main__":
    # Example usage
    pipeline = PipelineManager()
    success = pipeline.run_pipeline()
    print("Pipeline completed successfully" if success else "Pipeline failed") 