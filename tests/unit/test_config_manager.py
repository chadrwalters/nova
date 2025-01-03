"""Unit tests for Nova configuration management."""
import os
import pytest
import yaml
from pathlib import Path

from nova.config.manager import ConfigManager
from nova.config.settings import NovaConfig, CacheConfig, PipelineConfig

class TestConfigManagerBasics:
    """Tests for ConfigManager basic functionality."""
    
    def test_load_default_config(self, tmp_path: Path):
        """Test loading of default configuration."""
        # Create a default config file
        config_path = tmp_path / "default.yaml"
        config_data = {
            "base_dir": str(tmp_path / "base"),
            "input_dir": str(tmp_path / "input"),
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
        manager = ConfigManager(config_path=config_path, create_dirs=False)
        
        # Verify basic fields
        assert manager.base_dir == tmp_path / "base"
        assert manager.input_dir == tmp_path / "input"
        assert manager.output_dir == tmp_path / "output"
        assert manager.processing_dir == tmp_path / "processing"
        assert manager.cache_dir == tmp_path / "cache"
        assert manager.cache.enabled is True
        assert manager.cache.ttl == 3600
    
    def test_load_custom_config(self, tmp_path: Path):
        """Test loading of custom configuration file."""
        # Create a custom config with non-default values
        config_path = tmp_path / "custom.yaml"
        config_data = {
            "base_dir": str(tmp_path / "custom_base"),
            "input_dir": str(tmp_path / "custom_input"),
            "output_dir": str(tmp_path / "custom_output"),
            "processing_dir": str(tmp_path / "custom_processing"),
            "cache": {
                "dir": str(tmp_path / "custom_cache"),
                "enabled": False,
                "ttl": 7200
            },
            "pipeline": {
                "phases": ["parse", "finalize"]
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Initialize config manager
        manager = ConfigManager(config_path=config_path, create_dirs=False)
        
        # Verify custom values
        assert manager.base_dir == tmp_path / "custom_base"
        assert manager.input_dir == tmp_path / "custom_input"
        assert manager.output_dir == tmp_path / "custom_output"
        assert manager.processing_dir == tmp_path / "custom_processing"
        assert manager.cache_dir == tmp_path / "custom_cache"
        assert manager.cache.enabled is False
        assert manager.cache.ttl == 7200
        assert manager.pipeline.phases == ["parse", "finalize"]

class TestConfigManagerValidation:
    """Tests for configuration validation."""
    
    def test_required_fields(self, tmp_path: Path):
        """Test validation of required configuration fields."""
        # Create config with missing required fields
        config_path = tmp_path / "invalid.yaml"
        config_data = {
            # Missing base_dir and input_dir
            "output_dir": str(tmp_path / "output"),
            "processing_dir": str(tmp_path / "processing")
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Initialize config manager - should use default paths
        manager = ConfigManager(config_path=config_path, create_dirs=False)
        
        # Verify default values were used
        assert manager.base_dir.exists() or str(manager.base_dir).startswith("~")
        assert manager.input_dir.name == "_NovaInput"
        assert manager.output_dir == tmp_path / "output"
        assert manager.processing_dir == tmp_path / "processing"
    
    def test_field_types(self, tmp_path: Path):
        """Test validation of configuration field types."""
        # Create config with invalid field types
        config_path = tmp_path / "types.yaml"
        config_data = {
            "base_dir": str(tmp_path / "base"),
            "input_dir": str(tmp_path / "input"),
            "output_dir": str(tmp_path / "output"),
            "processing_dir": str(tmp_path / "processing"),
            "cache": {
                "dir": str(tmp_path / "cache"),
                "enabled": "yes",  # Should be boolean
                "ttl": "3600"  # Should be integer
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Initialize config manager
        with pytest.raises(ValueError):
            ConfigManager(config_path=config_path, create_dirs=False)

class TestConfigManagerPaths:
    """Tests for path handling in configuration."""
    
    def test_expand_variables(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test expansion of environment variables in paths."""
        # Set up test environment variables
        test_dir = str(tmp_path / "test_env")
        monkeypatch.setenv("NOVA_TEST_DIR", test_dir)
        
        # Create config with environment variables
        config_path = tmp_path / "env.yaml"
        config_data = {
            "base_dir": "${NOVA_TEST_DIR}/base",
            "input_dir": "${NOVA_TEST_DIR}/input",
            "output_dir": "${NOVA_TEST_DIR}/output",
            "processing_dir": "${NOVA_TEST_DIR}/processing",
            "cache": {
                "dir": "${NOVA_TEST_DIR}/cache"
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Initialize config manager
        manager = ConfigManager(config_path=config_path, create_dirs=False)
        
        # Verify variables were expanded
        assert str(manager.base_dir) == f"{test_dir}/base"
        assert str(manager.input_dir) == f"{test_dir}/input"
        assert str(manager.output_dir) == f"{test_dir}/output"
        assert str(manager.processing_dir) == f"{test_dir}/processing"
        assert str(manager.cache_dir) == f"{test_dir}/cache"
    
    def test_create_directories(self, tmp_path: Path):
        """Test creation of configured directories."""
        # Create config with non-existent directories
        config_path = tmp_path / "dirs.yaml"
        config_data = {
            "base_dir": str(tmp_path / "base"),
            "input_dir": str(tmp_path / "input"),
            "output_dir": str(tmp_path / "output"),
            "processing_dir": str(tmp_path / "processing"),
            "cache": {
                "dir": str(tmp_path / "cache")
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Initialize config manager with create_dirs=True
        manager = ConfigManager(config_path=config_path, create_dirs=True)
        
        # Verify directories were created
        assert manager.base_dir.exists()
        assert manager.input_dir.exists()
        assert manager.output_dir.exists()
        assert manager.processing_dir.exists()
        assert manager.cache_dir.exists()
        
        # Verify they are actually directories
        assert manager.base_dir.is_dir()
        assert manager.input_dir.is_dir()
        assert manager.output_dir.is_dir()
        assert manager.processing_dir.is_dir()
        assert manager.cache_dir.is_dir() 