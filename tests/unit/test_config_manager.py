"""Unit tests for configuration manager."""
import pytest
import yaml
from pathlib import Path
from nova.config.manager import ConfigManager
from nova.config.settings import NovaConfig, CacheConfig


@pytest.mark.unit
@pytest.mark.config
class TestConfigManager:
    """Test configuration manager functionality."""
    
    def test_load_default_config(self, mock_fs):
        """Test loading default configuration."""
        config_path = mock_fs["root"] / "config.yaml"
        config_data = {
            "base_dir": str(mock_fs["root"]),
            "input_dir": str(mock_fs["input"]),
            "output_dir": str(mock_fs["output"]),
            "processing_dir": str(mock_fs["processing"]),
            "cache": {
                "dir": str(mock_fs["cache"]),
                "enabled": True,
                "ttl": 3600
            }
        }
        
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        config = ConfigManager(config_path, create_dirs=False)
        assert str(config.base_dir) == str(mock_fs["root"])
        assert str(config.input_dir) == str(mock_fs["input"])
        assert str(config.output_dir) == str(mock_fs["output"])
        assert str(config.processing_dir) == str(mock_fs["processing"])
        assert str(config.cache_dir) == str(mock_fs["cache"])
    
    def test_config_validation(self, mock_fs):
        """Test configuration validation."""
        config_path = mock_fs["root"] / "config.yaml"
        
        # Missing required fields
        config_data = {
            "cache": {
                "dir": str(mock_fs["cache"]),
                "enabled": True,
                "ttl": 3600
            }
        }
        
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        with pytest.raises(ValueError):
            ConfigManager(config_path, create_dirs=False)
    
    def test_path_resolution(self, mock_fs):
        """Test path resolution."""
        config_path = mock_fs["root"] / "config.yaml"
        config_data = {
            "base_dir": "${TEST_BASE_DIR}",
            "input_dir": "${TEST_INPUT_DIR}",
            "output_dir": "${TEST_OUTPUT_DIR}",
            "processing_dir": "${TEST_PROCESSING_DIR}",
            "cache": {
                "dir": "${TEST_CACHE_DIR}",
                "enabled": True,
                "ttl": 3600
            }
        }
        
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        # Set environment variables
        import os
        os.environ["TEST_BASE_DIR"] = str(mock_fs["root"])
        os.environ["TEST_INPUT_DIR"] = str(mock_fs["input"])
        os.environ["TEST_OUTPUT_DIR"] = str(mock_fs["output"])
        os.environ["TEST_PROCESSING_DIR"] = str(mock_fs["processing"])
        os.environ["TEST_CACHE_DIR"] = str(mock_fs["cache"])
        
        config = ConfigManager(config_path, create_dirs=False)
        assert str(config.base_dir) == str(mock_fs["root"])
        assert str(config.input_dir) == str(mock_fs["input"])
        assert str(config.output_dir) == str(mock_fs["output"])
        assert str(config.processing_dir) == str(mock_fs["processing"])
        assert str(config.cache_dir) == str(mock_fs["cache"]) 