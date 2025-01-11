from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class Attachment:
    path: Path
    original_name: str
    content_type: str
    converted_text: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class Note:
    title: str
    content: str
    path: Path
    created_at: datetime
    modified_at: datetime
    tags: List[str] = field(default_factory=list)
    attachments: List[Attachment] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class MarkdownCorpus:
    notes: List[Note]
    root_path: Path
    metadata: Dict[str, str] = field(default_factory=dict)
    
    def add_note(self, note: Note) -> None:
        """Add a note to the corpus."""
        self.notes.append(note)
    
    def get_note_by_title(self, title: str) -> Optional[Note]:
        """Get a note by its title."""
        for note in self.notes:
            if note.title == title:
                return note
        return None
    
    def get_notes_by_tag(self, tag: str) -> List[Note]:
        """Get all notes with a specific tag."""
        return [note for note in self.notes if tag in note.tags] 