"""State management for Nova Document Processor."""

import json
import os
import xxhash
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict

from .logging import get_logger
from .errors import ProcessingError

logger = get_logger(__name__)

@dataclass
class ProcessingVersion:
    """Version information for processing components."""
    global_version: str = "1.0"
    openai_model: str = "gpt-4-turbo-2024-04-09"
    image_processor: str = "1.0"
    markdown_parser: str = "1.0"
    office_converter: str = "1.0"

@dataclass
class FileState:
    """State information for a file."""
    path: str
    hash: str
    size: int
    last_processed: str
    
@dataclass
class ProcessingState:
    """Complete state for a markdown file and its attachments."""
    file_info: FileState
    processing_version: ProcessingVersion
    attachments: Dict[str, FileState]

class StateManager:
    """Manages processing state for markdown files and attachments."""
    
    def __init__(self, processing_dir: Path):
        """Initialize state manager."""
        self.processing_dir = processing_dir
        self.state_dir = processing_dir / ".state"
        self.state_dir.mkdir(exist_ok=True)
        
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate xxHash64 hash of a file."""
        hasher = xxhash.xxh64()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _get_state_path(self, markdown_path: Path) -> Path:
        """Get path to state file for a markdown file."""
        rel_path = markdown_path.relative_to(os.getenv('NOVA_INPUT_DIR'))
        return self.state_dir / f"{rel_path.stem}.state.json"
    
    def _get_file_state(self, file_path: Path) -> FileState:
        """Get current state of a file."""
        return FileState(
            path=str(file_path.relative_to(os.getenv('NOVA_INPUT_DIR'))),
            hash=self._calculate_file_hash(file_path),
            size=file_path.stat().st_size,
            last_processed=datetime.now(timezone.utc).isoformat()
        )
    
    def load_state(self, markdown_path: Path) -> Optional[ProcessingState]:
        """Load state for a markdown file if it exists."""
        state_path = self._get_state_path(markdown_path)
        if not state_path.exists():
            return None
            
        try:
            with open(state_path, 'r') as f:
                data = json.load(f)
                return ProcessingState(
                    file_info=FileState(**data['file_info']),
                    processing_version=ProcessingVersion(**data['processing_version']),
                    attachments={k: FileState(**v) for k, v in data['attachments'].items()}
                )
        except Exception as e:
            logger.warning(f"Failed to load state for {markdown_path}: {e}")
            return None
    
    def save_state(self, markdown_path: Path, state: ProcessingState) -> None:
        """Save state for a markdown file."""
        state_path = self._get_state_path(markdown_path)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(state_path, 'w') as f:
                json.dump(asdict(state), f, indent=2)
        except Exception as e:
            raise ProcessingError(f"Failed to save state for {markdown_path}: {e}")
    
    def needs_processing(self, markdown_path: Path, check_attachments: bool = True) -> bool:
        """Check if a markdown file needs processing."""
        if not markdown_path.exists():
            return False
            
        current_state = self._get_file_state(markdown_path)
        saved_state = self.load_state(markdown_path)
        
        # If no saved state, needs processing
        if not saved_state:
            return True
            
        # Check if markdown file changed
        if (current_state.hash != saved_state.file_info.hash or
            current_state.size != saved_state.file_info.size):
            return True
            
        # Check if processing version changed
        current_version = ProcessingVersion()
        if asdict(current_version) != asdict(saved_state.processing_version):
            return True
            
        # Check attachments if requested
        if check_attachments:
            attachments_dir = markdown_path.parent / markdown_path.stem
            if attachments_dir.exists() and attachments_dir.is_dir():
                current_attachments = {
                    f.name: self._get_file_state(f)
                    for f in attachments_dir.iterdir()
                    if f.is_file()
                }
                
                # Check for new or modified attachments
                for name, state in current_attachments.items():
                    if name not in saved_state.attachments:
                        return True
                    saved = saved_state.attachments[name]
                    if state.hash != saved.hash or state.size != saved.size:
                        return True
                
                # Check for deleted attachments
                if set(saved_state.attachments) != set(current_attachments):
                    return True
                    
        return False
    
    def update_state(self, markdown_path: Path) -> None:
        """Update state after successful processing."""
        current_state = ProcessingState(
            file_info=self._get_file_state(markdown_path),
            processing_version=ProcessingVersion(),
            attachments={}
        )
        
        # Add attachments if they exist
        attachments_dir = markdown_path.parent / markdown_path.stem
        if attachments_dir.exists() and attachments_dir.is_dir():
            current_state.attachments = {
                f.name: self._get_file_state(f)
                for f in attachments_dir.iterdir()
                if f.is_file()
            }
            
        self.save_state(markdown_path, current_state)
    
    def clear_state(self, markdown_path: Optional[Path] = None) -> None:
        """Clear processing state."""
        if markdown_path:
            state_path = self._get_state_path(markdown_path)
            if state_path.exists():
                state_path.unlink()
        else:
            # Clear all state
            if self.state_dir.exists():
                for state_file in self.state_dir.glob("*.state.json"):
                    state_file.unlink() 