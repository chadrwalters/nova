"""Integration tests for Nova pipeline."""
import os
import pytest
import yaml
import shutil
from pathlib import Path

from nova.config.manager import ConfigManager
from nova.handlers.markdown import MarkdownHandler
from nova.handlers.document import DocumentHandler
from nova.handlers.text import TextHandler
from nova.handlers.image import ImageHandler
from nova.core.pipeline import NovaPipeline
from nova.utils.test_utils import create_test_files

class TestPipelineEndToEnd:
    """End-to-end tests for Nova pipeline."""
    
    @pytest.mark.asyncio
    async def test_markdown_end_to_end(self, tmp_path: Path):
        """Test end-to-end pipeline processing of markdown files."""
        # Create test config
        config_path = tmp_path / "test_config.yaml"
        config_data = {
            "base_dir": str(tmp_path / "base"),
            "input_dir": str(tmp_path / "_NovaInput"),
            "output_dir": str(tmp_path / "output"),
            "processing_dir": str(tmp_path / "processing"),
            "cache": {
                "dir": str(tmp_path / "cache"),
                "enabled": True,
                "ttl": 3600
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Initialize config manager
        config = ConfigManager(config_path=config_path, create_dirs=True)
        
        # Create test files in _NovaInput directory
        create_test_files(config.input_dir)
        
        # Initialize pipeline
        pipeline = NovaPipeline(config)
        
        # Process files
        await pipeline.process_directory(config.input_dir)
        
        # Verify output
        assert (config.output_dir / "test.parsed.md").exists()
        assert (config.output_dir / "test.metadata.json").exists()
    
    @pytest.mark.asyncio
    async def test_pipeline_with_all_formats(self, tmp_path: Path):
        """Test pipeline processing of all supported file formats."""
        # Create test config
        config_path = tmp_path / "test_config.yaml"
        config_data = {
            "base_dir": str(tmp_path / "base"),
            "input_dir": str(tmp_path / "_NovaInput"),
            "output_dir": str(tmp_path / "output"),
            "processing_dir": str(tmp_path / "processing"),
            "cache": {
                "dir": str(tmp_path / "cache"),
                "enabled": True,
                "ttl": 3600
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Initialize config manager
        config = ConfigManager(config_path=config_path, create_dirs=True)
        
        # Create test files in _NovaInput directory
        create_test_files(config.input_dir)
        
        # Initialize pipeline
        pipeline = NovaPipeline(config)
        
        # Process files
        await pipeline.process_directory(config.input_dir)
        
        # Verify output for each format
        assert (config.output_dir / "test.parsed.md").exists()
        assert (config.output_dir / "test.pdf.parsed.md").exists()
        assert (config.output_dir / "test.txt.parsed.md").exists()
        assert (config.output_dir / "test.jpg.parsed.md").exists()
    
    @pytest.mark.asyncio
    async def test_pipeline_handles_unsupported_file(self, tmp_path: Path):
        """Test pipeline handling of unsupported file types."""
        # Create test config
        config_path = tmp_path / "test_config.yaml"
        config_data = {
            "base_dir": str(tmp_path / "base"),
            "input_dir": str(tmp_path / "_NovaInput"),
            "output_dir": str(tmp_path / "output"),
            "processing_dir": str(tmp_path / "processing"),
            "cache": {
                "dir": str(tmp_path / "cache"),
                "enabled": True,
                "ttl": 3600
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Initialize config manager
        config = ConfigManager(config_path=config_path, create_dirs=True)
        
        # Create unsupported file in _NovaInput directory
        unsupported_file = config.input_dir / "test.xyz"
        unsupported_file.parent.mkdir(parents=True, exist_ok=True)
        unsupported_file.write_text("test content")
        
        # Initialize pipeline
        pipeline = NovaPipeline(config)
        
        # Process files - should skip unsupported file
        await pipeline.process_directory(config.input_dir)
        
        # Verify unsupported file was skipped
        assert not (config.output_dir / "test.xyz.parsed.md").exists()
    
    @pytest.mark.skip(reason="Requires OpenAI API key")
    @pytest.mark.asyncio
    async def test_pipeline_with_ai_analysis(self, tmp_path: Path):
        """Test pipeline with AI analysis enabled."""
        # Create test config with OpenAI settings
        config_path = tmp_path / "test_config.yaml"
        config_data = {
            "base_dir": str(tmp_path / "base"),
            "input_dir": str(tmp_path / "_NovaInput"),
            "output_dir": str(tmp_path / "output"),
            "processing_dir": str(tmp_path / "processing"),
            "cache": {
                "dir": str(tmp_path / "cache"),
                "enabled": True,
                "ttl": 3600
            },
            "apis": {
                "openai": {
                    "api_key": os.environ.get("OPENAI_API_KEY"),
                    "model": "gpt-4o",
                    "max_tokens": 500
                }
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Initialize config manager
        config = ConfigManager(config_path=config_path, create_dirs=True)
        
        # Create test files in _NovaInput directory
        create_test_files(config.input_dir)
        
        # Initialize pipeline
        pipeline = NovaPipeline(config)
        
        # Process files
        await pipeline.process_directory(config.input_dir)
        
        # Verify AI analysis output
        assert (config.output_dir / "test.jpg.parsed.md").exists()
        content = (config.output_dir / "test.jpg.parsed.md").read_text()
        assert "AI Analysis" in content
    
    @pytest.mark.asyncio
    async def test_pipeline_state_tracking(self, tmp_path: Path):
        """Test pipeline state tracking and error handling."""
        # Create test config
        config_path = tmp_path / "test_config.yaml"
        config_data = {
            "base_dir": str(tmp_path / "base"),
            "input_dir": str(tmp_path / "_NovaInput"),
            "output_dir": str(tmp_path / "output"),
            "processing_dir": str(tmp_path / "processing"),
            "cache": {
                "dir": str(tmp_path / "cache"),
                "enabled": True,
                "ttl": 3600
            },
            "debug": {
                "enabled": True,
                "state_logging": True
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Initialize config manager
        config = ConfigManager(config_path=config_path, create_dirs=True)
        
        # Create test files in _NovaInput directory
        create_test_files(config.input_dir)
        
        # Initialize pipeline
        pipeline = NovaPipeline(config)
        
        # Process files
        await pipeline.process_directory(config.input_dir)
        
        # Verify state tracking
        assert pipeline.state is not None
        assert len(pipeline.state["parse"]["successful_files"]) > 0
        assert len(pipeline.state["parse"]["failed_files"]) == 0 