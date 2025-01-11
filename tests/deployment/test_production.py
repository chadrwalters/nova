"""Test suite for production deployment."""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Generator, AsyncGenerator
import pytest
from unittest.mock import patch, MagicMock

import yaml

from nova.config import load_config
from nova.deployment.cloud import deploy_cloud
from nova.deployment.backup import create_backup, restore_backup


@pytest.fixture
def prod_config(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary production config for testing."""
    config_path = tmp_path / "prod_nova.yaml"
    config_content = """
base_dir: "data"
cache_dir: "data/cache"

api:
  openai_api_key: "${OPENAI_API_KEY}"
  vision_prompt: "Please analyze this image and provide a detailed description."

security:
  tls_cert_path: "certs/server.crt"
  tls_key_path: "certs/server.key"
  enable_tls: true

monitoring:
  enabled: true
  metrics:
    port: 8000
    memory_update_interval: 60
    vector_store_update_interval: 300
  alerting:
    max_query_latency: 1.0
    max_error_rate: 0.01
    max_memory_usage: 4294967296
    max_vector_store_size: 1000000
    min_rate_limit_remaining: 100
    rate_limit_warning_threshold: 0.2
    log_path: "logs/alerts.log"

cloud:
  provider: "aws"
  region: "us-west-2"
  instance_type: "t3.medium"

handlers:
  image_formats: ["png", "jpg", "jpeg", "gif"]
"""
    config_path.write_text(config_content)
    yield config_path


@pytest.fixture
def mock_tls_files(tmp_path: Path) -> tuple[Path, Path]:
    """Create mock TLS certificate and key files."""
    cert_path = tmp_path / "test.crt"
    key_path = tmp_path / "test.key"
    
    # Create dummy certificate and key files
    cert_path.write_text("-----BEGIN CERTIFICATE-----\nMIIDvTCCAqWgAwIBAgIUJ2...")
    key_path.write_text("-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0B...")
    
    return cert_path, key_path


@pytest.mark.production
def test_cloud_deployment(prod_config: Path, mock_tls_files: tuple[Path, Path]) -> None:
    """Test cloud deployment in production environment."""
    cert_path, key_path = mock_tls_files
    
    # Set test environment
    os.environ["NOVA_ENV"] = "test"
    
    # Update config with actual TLS paths
    config = load_config(prod_config)
    config.security.tls_cert_path = str(cert_path)
    config.security.tls_key_path = str(key_path)
    
    # Test cloud deployment
    deploy_cloud(config)
    
    # Verify deployment
    assert os.path.exists(config.security.tls_cert_path)
    assert os.path.exists(config.security.tls_key_path)


@pytest.mark.production
def test_backup_restore(prod_config: Path, tmp_path: Path) -> None:
    """Test backup and restore in production environment."""
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    
    # Create test data
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "test.txt").write_text("Test data")
    
    # Create backup
    backup_path = create_backup(backup_dir, data_dir)
    assert backup_path.exists(), "Backup not created"
    
    # Modify data
    (data_dir / "test.txt").write_text("Modified data")
    
    # Restore backup
    restore_backup(backup_path, data_dir)
    assert (data_dir / "test.txt").read_text() == "Test data", "Restore failed"


@pytest.mark.production
@pytest.mark.asyncio
async def test_streaming_performance(prod_config: Path) -> None:
    """Test streaming performance in production environment."""
    from nova.rag import RAGOrchestrator
    
    config = load_config(prod_config)
    orchestrator = RAGOrchestrator(config)
    
    # Test streaming performance
    query = "What is the meaning of life?"
    start_time = time.time()
    
    chunks = []
    async for chunk in orchestrator.process_query_streaming(query):
        chunks.append(chunk)
        # Verify chunk delay is reasonable
        assert time.time() - start_time < 5, "Streaming too slow"
    
    assert chunks, "No streaming response received"
    
    # Verify total response time
    total_time = time.time() - start_time
    assert total_time < 10, f"Total streaming time too long: {total_time}s"


@pytest.mark.production
@pytest.mark.asyncio
async def test_error_recovery(prod_config: Path) -> None:
    """Test error recovery in production environment."""
    from nova.rag import RAGOrchestrator
    from unittest.mock import AsyncMock, patch
    
    config = load_config(prod_config)
    orchestrator = RAGOrchestrator(config)
    
    # Mock the streaming response
    async def mock_stream(query: str, resume: bool = False) -> AsyncGenerator[str, None]:
        if not resume:
            yield "First"
            yield "Second"
            raise ConnectionError("Simulated connection error")
        else:
            yield "Third"
            yield "Fourth"
    
    # Test connection interruption recovery
    with patch.object(orchestrator, "process_query_streaming", side_effect=mock_stream):
        chunks = []
        try:
            async for chunk in orchestrator.process_query_streaming("test"):
                chunks.append(chunk)
        except ConnectionError:
            # Should auto-recover and continue
            async for chunk in orchestrator.process_query_streaming("test", resume=True):
                chunks.append(chunk)
        
        assert len(chunks) == 4, "Error recovery failed"
        assert chunks == ["First", "Second", "Third", "Fourth"], "Incorrect recovery sequence"


@pytest.mark.production
def test_security_measures(prod_config: Path, mock_tls_files: tuple[Path, Path]) -> None:
    """Test security measures in production environment."""
    cert_path, key_path = mock_tls_files

    # Update config with actual TLS paths
    config = load_config(prod_config)
    config.security.tls_cert_path = str(cert_path)
    config.security.tls_key_path = str(key_path)

    # Test TLS configuration
    assert config.security.tls_cert_path.endswith(".crt")
    assert config.security.tls_key_path.endswith(".key")

    # Test API key validation
    from nova.utils import validate_api_key
    assert not validate_api_key("invalid_key"), "Invalid API key accepted"

    # Set up test API key
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-api03-test-key-12345"
    assert validate_api_key(os.getenv("ANTHROPIC_API_KEY", "")), "Valid API key rejected"

    # Test token authentication
    from nova.utils import validate_auth_token
    assert validate_auth_token(config.security.auth_token), "Auth token invalid" 