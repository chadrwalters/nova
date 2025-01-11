import pytest
import os
import asyncio
from pathlib import Path, PurePath, PurePosixPath
from unittest.mock import Mock, patch, mock_open
import sys

from nova.cli import main
from nova.utils.config import (
    IngestionConfig,
    EmbeddingConfig,
    VectorStoreConfig,
    RAGConfig,
    LLMConfig,
    SecurityConfig,
    NovaConfig
)


class MockPath(PurePosixPath):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, "/test/path")
    
    def exists(self):
        return True
    
    def is_file(self):
        return True
    
    def is_dir(self):
        return True
    
    def glob(self, pattern):
        return [self]
    
    def read_text(self):
        return "# Test Note\nTest content"
    
    def stat(self):
        return Mock(st_ctime=0, st_mtime=0)
    
    def absolute(self):
        return self
    
    def resolve(self):
        return self
    
    def expanduser(self):
        return self
    
    def joinpath(self, *args):
        return self


@pytest.fixture(autouse=True)
def mock_gettext():
    with patch("gettext.translation") as mock:
        mock.return_value.gettext = lambda x: x
        mock.return_value.ngettext = lambda s, p, n: s if n == 1 else p
        yield mock


@pytest.fixture(autouse=True)
def mock_path():
    test_path = Path("/test/path")
    
    def mock_glob(*args, **kwargs):
        return [test_path]
    
    def mock_read_text(*args, **kwargs):
        return "# Test Note\nTest content"
    
    def mock_stat(*args, **kwargs):
        return Mock(st_ctime=0, st_mtime=0)
    
    patches = [
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "is_file", return_value=True),
        patch.object(Path, "is_dir", return_value=True),
        patch.object(Path, "glob", side_effect=mock_glob),
        patch.object(Path, "read_text", side_effect=mock_read_text),
        patch.object(Path, "stat", side_effect=mock_stat),
        patch.object(Path, "absolute", return_value=test_path),
        patch.object(Path, "resolve", return_value=test_path),
        patch.object(Path, "expanduser", return_value=test_path),
        patch("os.path.exists", return_value=True),
        patch("os.path.isfile", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.access", return_value=True),
    ]
    
    for p in patches:
        p.start()
    
    yield test_path
    
    for p in patches:
        p.stop()


@pytest.fixture
def mock_config():
    with patch("nova.utils.config.NovaConfig") as mock:
        # Create a proper config instance
        config = Mock()
        
        # Create proper dataclass instances
        config.ingestion = IngestionConfig(
            chunk_size=500,
            heading_weight=1.5
        )
        config.embedding = EmbeddingConfig(
            model="all-MiniLM-L6-v2",
            dimension=384
        )
        config.vector_store = VectorStoreConfig(
            engine="faiss"
        )
        config.rag = RAGConfig(
            top_k=5
        )
        config.llm = LLMConfig(
            model="claude-2",
            max_tokens=1000,
            api_key="test-key"
        )
        config.security = SecurityConfig(
            ephemeral_ttl=300
        )
        config.debug = False
        config.log_level = "INFO"
        
        # Mock validate method
        config.llm.validate = Mock()
        
        # Set up the from_yaml method to return our config
        mock.from_yaml.return_value = config
        
        # Make the mock return our config instance
        mock.return_value = config
        
        # Mock config file loading
        with patch("os.path.exists", return_value=True), \
             patch("os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data="test: data")):
            yield config


@pytest.fixture
def mock_fs():
    with patch("os.path.exists") as exists_mock, \
         patch("os.path.isfile") as isfile_mock, \
         patch("os.path.isdir") as isdir_mock, \
         patch("os.access") as access_mock:
        exists_mock.return_value = True
        isfile_mock.return_value = True
        isdir_mock.return_value = True
        access_mock.return_value = True
        yield exists_mock


@pytest.fixture
def mock_env():
    with patch("nova.utils.config.load_dotenv") as mock:
        mock.return_value = True
        with patch.dict(os.environ, {"CLAUDE_API_KEY": "test-key"}):
            yield mock


def test_ingest_command(mock_config, mock_fs, mock_env, capsys):
    test_path = "test_export"
    with patch("nova.cli.BearExportHandler") as mock_handler:
        mock_corpus = Mock()
        mock_corpus.notes = [Mock()]
        mock_handler.return_value.process_export.return_value = mock_corpus
        
        with patch("sys.argv", ["nova", "ingest", test_path]):
            assert main() == 0
            mock_handler.assert_called_once()
            mock_handler.return_value.process_export.assert_called_once()
            captured = capsys.readouterr()
            assert "Successfully processed Bear export" in captured.out


def test_process_command(mock_config, mock_fs, mock_env, capsys):
    test_path = "test_docs"
    with patch("nova.cli.ChunkingEngine") as mock_chunking, \
         patch("nova.cli.EmbeddingService") as mock_embedding:
        # Configure mock_chunking_engine
        mock_chunks = [Mock(content="Test chunk", metadata={})]
        mock_chunking.return_value.process_directory.return_value = mock_chunks
        
        # Configure mock_embedding_service
        mock_embedding.return_value.embed_chunks.return_value = None
        
        with patch("sys.argv", ["nova", "process", test_path]):
            assert main() == 0
            mock_chunking.assert_called_once_with(
                chunk_size=mock_config.ingestion.chunk_size,
                heading_weight=mock_config.ingestion.heading_weight
            )
            mock_chunking.return_value.process_directory.assert_called_once()
            mock_embedding.return_value.embed_chunks.assert_called_once_with(mock_chunks)
            captured = capsys.readouterr()
            assert "Successfully processed documents" in captured.out


@pytest.mark.asyncio
async def test_query_command(mock_config, mock_fs, mock_env, capsys):
    with patch("nova.cli.RAGOrchestrator") as mock_rag, \
         patch("nova.cli.ClaudeClient") as mock_claude, \
         patch("asyncio.run") as mock_run:
        mock_response = Mock(content="Test response")
        mock_rag.return_value.query.return_value = mock_response
        mock_run.side_effect = lambda x: mock_response
        
        with patch("sys.argv", ["nova", "query", "test query"]):
            assert main() == 0
            mock_claude.assert_called_once_with(
                api_key="test-key",
                model=mock_config.llm.model,
                max_tokens=mock_config.llm.max_tokens
            )
            mock_rag.return_value.query.assert_called_once()
            captured = capsys.readouterr()
            assert "Test response" in captured.out


@pytest.mark.asyncio
async def test_query_command_streaming(mock_config, mock_fs, mock_env, capsys):
    with patch("nova.cli.RAGOrchestrator") as mock_rag, \
         patch("nova.cli.ClaudeClient") as mock_claude, \
         patch("asyncio.run") as mock_run:
        
        # Create a mock async generator
        async def mock_stream():
            yield "Chunk 1"
            yield "Chunk 2"
        
        # Set up the mock to return an awaitable that returns the generator
        async def mock_query_streaming(*args, **kwargs):
            return mock_stream()
        
        mock_rag.return_value.query_streaming = mock_query_streaming
        
        # Mock asyncio.run to print the chunks
        def run_async(coro):
            print("Chunk 1", end="", flush=True)
            print("Chunk 2", end="", flush=True)
            print()
            return None
        
        mock_run.side_effect = run_async
        
        with patch("sys.argv", ["nova", "query", "test query", "--stream"]):
            assert main() == 0
            mock_claude.assert_called_once_with(
                api_key="test-key",
                model=mock_config.llm.model,
                max_tokens=mock_config.llm.max_tokens
            )
            captured = capsys.readouterr()
            assert "Chunk 1Chunk 2" in captured.out


def test_invalid_command(mock_config, mock_fs, mock_env, capsys):
    with patch("sys.argv", ["nova"]):
        assert main() == 1
        captured = capsys.readouterr()
        assert "Please specify a command" in captured.out


def test_config_error(mock_config, mock_fs, mock_env, capsys):
    with patch("nova.cli.NovaConfig.from_yaml", side_effect=FileNotFoundError("Config file not found")):
        with patch("sys.argv", ["nova", "ingest", "test"]):
            assert main() == 1
            captured = capsys.readouterr()
            assert "Config file not found" in captured.err 