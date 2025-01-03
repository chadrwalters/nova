"""Common test fixtures and configuration for Nova tests."""
import os
import pytest
from pathlib import Path
from typing import Generator, Dict, Set, Any
from dataclasses import dataclass, field
from nova.config.settings import NovaConfig, PipelineConfig, LoggingConfig, CacheConfig, DebugConfig
from nova.config.manager import ConfigManager

@dataclass
class PipelineState:
    """Mock pipeline state for testing."""
    input_dir: Path
    output_dir: Path
    processing_dir: Path
    file_metadata: Dict[str, Any] = field(default_factory=dict)
    referenced_files: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Dict] = field(default_factory=lambda: {
        'parse': {
            'successful_files': set(),
            'failed_files': set(),
            'skipped_files': set(),
            'unchanged_files': set(),
            'reprocessed_files': set(),
            'file_type_stats': {},
            'attachments': {}
        },
        'disassemble': {
            'successful_files': set(),
            'failed_files': set(),
            'skipped_files': set(),
            'unchanged_files': set(),
            'reprocessed_files': set(),
            'attachments': {},
            'stats': {
                'total_processed': 0,
                'summary_files': {
                    'created': 0,
                    'empty': 0,
                    'failed': 0
                },
                'raw_notes_files': {
                    'created': 0,
                    'empty': 0,
                    'failed': 0
                },
                'attachments': {
                    'copied': 0,
                    'failed': 0
                }
            }
        },
        'split': {
            'successful_files': set(),
            'failed_files': set(),
            'skipped_files': set(),
            'unchanged_files': set(),
            'reprocessed_files': set(),
            'section_stats': {},
            'summary_sections': 0,
            'raw_notes_sections': 0,
            'attachments': 0
        },
        'finalize': {
            'successful_files': set(),
            'failed_files': set(),
            'skipped_files': set(),
            'unchanged_files': set(),
            'reprocessed_files': set(),
            'reference_validation': {
                'total_references': 0,
                'valid_references': 0,
                'invalid_references': 0,
                'missing_references': 0
            }
        }
    })

    def reset(self):
        """Reset the pipeline state."""
        self.file_metadata.clear()
        self.state = {
            'parse': {
                'successful_files': set(),
                'failed_files': set(),
                'skipped_files': set(),
                'unchanged_files': set(),
                'reprocessed_files': set(),
                'file_type_stats': {},
                'attachments': {}
            },
            'disassemble': {
                'successful_files': set(),
                'failed_files': set(),
                'skipped_files': set(),
                'unchanged_files': set(),
                'reprocessed_files': set(),
                'attachments': {},
                'stats': {
                    'total_processed': 0,
                    'summary_files': {
                        'created': 0,
                        'empty': 0,
                        'failed': 0
                    },
                    'raw_notes_files': {
                        'created': 0,
                        'empty': 0,
                        'failed': 0
                    },
                    'attachments': {
                        'copied': 0,
                        'failed': 0
                    }
                }
            },
            'split': {
                'successful_files': set(),
                'failed_files': set(),
                'skipped_files': set(),
                'unchanged_files': set(),
                'reprocessed_files': set(),
                'section_stats': {},
                'summary_sections': 0,
                'raw_notes_sections': 0,
                'attachments': 0
            },
            'finalize': {
                'successful_files': set(),
                'failed_files': set(),
                'skipped_files': set(),
                'unchanged_files': set(),
                'reprocessed_files': set(),
                'reference_validation': {
                    'total_references': 0,
                    'valid_references': 0,
                    'invalid_references': 0,
                    'missing_references': 0
                }
            }
        }

@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create and return a temporary directory for test data."""
    return tmp_path / "test_data"

@pytest.fixture
def input_dir(test_data_dir: Path) -> Path:
    """Create and return a temporary input directory."""
    input_dir = test_data_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    return input_dir

@pytest.fixture
def output_dir(test_data_dir: Path) -> Path:
    """Create and return a temporary output directory."""
    output_dir = test_data_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

@pytest.fixture
def processing_dir(test_data_dir: Path) -> Path:
    """Create and return a temporary processing directory."""
    processing_dir = test_data_dir / "processing"
    processing_dir.mkdir(parents=True, exist_ok=True)
    return processing_dir

@pytest.fixture
def mock_config(tmp_path: Path) -> ConfigManager:
    """Create a mock ConfigManager for testing."""
    config = NovaConfig(
        base_dir=tmp_path / "base",
        input_dir=tmp_path / "input",
        output_dir=tmp_path / "output",
        processing_dir=tmp_path / "processing",
        cache=CacheConfig(
            dir=tmp_path / "cache",
            enabled=True,
            ttl=3600
        ),
        pipeline=PipelineConfig(),
        logging=LoggingConfig(log_dir=tmp_path / "logs"),
        debug=DebugConfig()
    )
    manager = ConfigManager.__new__(ConfigManager)
    manager.config = config
    return manager

@pytest.fixture
def pipeline_state(test_data_dir: Path) -> PipelineState:
    """Provide a fresh pipeline state for each test."""
    input_dir = test_data_dir / "input"
    output_dir = test_data_dir / "output"
    processing_dir = test_data_dir / "processing"
    
    # Create directories
    for dir_path in [input_dir, output_dir, processing_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    state = PipelineState(
        input_dir=input_dir,
        output_dir=output_dir,
        processing_dir=processing_dir
    )
    yield state
    state.reset()

@pytest.fixture
def phase_output_dir(test_data_dir: Path, request: pytest.FixtureRequest) -> Path:
    """Create and return a phase-specific output directory."""
    phase_name = request.node.get_closest_marker("phase")
    if not phase_name:
        pytest.skip("Test requires @pytest.mark.phase('phase_name')")
    
    phase_dir = test_data_dir / f"{phase_name.args[0]}_output"
    phase_dir.mkdir(parents=True, exist_ok=True)
    return phase_dir

@pytest.fixture(autouse=True)
def cleanup_test_files(request: pytest.FixtureRequest, test_data_dir: Path) -> Generator:
    """Automatically clean up test files after each test."""
    yield
    
    # Get the test function name and class
    test_name = request.node.name
    test_class = request.node.cls.__name__ if request.node.cls else None
    
    # Clean up phase-specific directories if this is a phase test
    phase_marker = request.node.get_closest_marker("phase")
    if phase_marker:
        phase_dir = test_data_dir / f"{phase_marker.args[0]}_output"
        if phase_dir.exists():
            for file in phase_dir.glob("*"):
                if file.is_file():
                    file.unlink()
            phase_dir.rmdir()
    
    # Clean up any test-specific files in input/output dirs
    for dir_path in [test_data_dir / "input", test_data_dir / "output"]:
        if dir_path.exists():
            for file in dir_path.glob("*"):
                if file.is_file():
                    file.unlink()

@pytest.fixture
def mock_file_metadata() -> Dict[str, Any]:
    """Return a mock file metadata structure."""
    return {
        "processed": False,
        "errors": [],
        "output_files": [],
        "attachments": [],
        "references": [],
        "metrics": {
            "parse_time": 0.0,
            "process_time": 0.0
        }
    }

def pytest_configure(config):
    """Add custom markers to pytest."""
    config.addinivalue_line("markers", "phase(name): mark test as belonging to a specific pipeline phase")
    config.addinivalue_line("markers", "requires_state: mark test as requiring pipeline state tracking") 

@pytest.fixture
def use_openai_api(request):
    """Control whether tests should use the actual OpenAI API.
    
    By default, returns False. To enable API calls, run pytest with:
    pytest --openai-api
    """
    return request.config.getoption("--openai-api", default=False)

@pytest.fixture
def mock_openai_response():
    """Provide mock responses for OpenAI API calls."""
    return {
        "image_analysis": "This is a mock image analysis response.",
        "text_analysis": "This is a mock text analysis response.",
        "summary": "This is a mock summary response."
    }

def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--openai-api",
        action="store_true",
        default=False,
        help="Run tests that make actual OpenAI API calls"
    ) 