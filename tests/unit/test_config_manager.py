"""Unit tests for configuration manager."""
import pytest
import yaml
from pathlib import Path
from nova.config.manager import ConfigManager
from nova.config.settings import NovaConfig, CacheConfig
from io import StringIO


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
    
    def test_config_validation(self, mock_fs, monkeypatch):
        """Test configuration validation."""
        config_path = mock_fs["root"] / "config.yaml"
        
        # Mock the default config loading to return empty config
        original_open = open
        def mock_open(*args, **kwargs):
            if str(args[0]).endswith('default.yaml'):
                return StringIO("{}")
            return original_open(*args, **kwargs)
        
        monkeypatch.setattr("builtins.open", mock_open)
        
        # Missing required fields - only include cache
        config_data = {
            "cache": {
                "dir": str(mock_fs["cache"]),
                "enabled": True,
                "ttl": 3600
            }
        }
        
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        with pytest.raises(ValueError, match="Missing required configuration fields"):
            ConfigManager(config_path, create_dirs=False)
            
        # Test invalid cache configuration
        config_data = {
            "base_dir": str(mock_fs["root"]),
            "input_dir": str(mock_fs["input"]),
            "output_dir": str(mock_fs["output"]),
            "processing_dir": str(mock_fs["processing"]),
            "cache": "invalid"  # Should be a dictionary
        }
        
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
            
        with pytest.raises(ValueError, match="Cache configuration must be a dictionary"):
            ConfigManager(config_path, create_dirs=False)
            
        # Test missing cache dir
        config_data = {
            "base_dir": str(mock_fs["root"]),
            "input_dir": str(mock_fs["input"]),
            "output_dir": str(mock_fs["output"]),
            "processing_dir": str(mock_fs["processing"]),
            "cache": {
                "enabled": True,
                "ttl": 3600
            }
        }
        
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
            
        with pytest.raises(ValueError, match="Cache configuration missing required field: dir"):
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