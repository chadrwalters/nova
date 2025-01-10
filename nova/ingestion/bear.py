import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nova.ingestion.types import Attachment, MarkdownCorpus, Note

class BearExportHandler:
    def __init__(self, export_path: Path):
        self.export_path = export_path
        self.attachments_dir = export_path / "assets"
        
        if not export_path.exists():
            raise FileNotFoundError(f"Export path not found: {export_path}")
        
        if not self.attachments_dir.exists():
            raise FileNotFoundError(f"Attachments directory not found: {self.attachments_dir}")
    
    def process_export(self) -> MarkdownCorpus:
        """Process the entire Bear export directory."""
        notes = []
        for md_file in self.export_path.glob("*.md"):
            if note := self._process_note(md_file):
                notes.append(note)
        
        return MarkdownCorpus(
            notes=notes,
            root_path=self.export_path,
            metadata={"source": "bear_export"}
        )
    
    def _process_note(self, note_path: Path) -> Optional[Note]:
        """Process a single note file."""
        try:
            content = note_path.read_text()
            title, content = self._extract_title(content)
            tags = self._extract_tags(content)
            attachments = self._process_attachments(content)
            
            # Get file stats for timestamps
            stats = note_path.stat()
            created_at = datetime.fromtimestamp(stats.st_ctime)
            modified_at = datetime.fromtimestamp(stats.st_mtime)
            
            return Note(
                title=title,
                content=content,
                path=note_path,
                created_at=created_at,
                modified_at=modified_at,
                tags=tags,
                attachments=attachments,
                metadata={"source": "bear"}
            )
        except Exception as e:
            print(f"Error processing note {note_path}: {e}")
            return None
    
    def _extract_title(self, content: str) -> Tuple[str, str]:
        """Extract title from note content."""
        lines = content.split("\n")
        title = "Untitled Note"
        
        # Look for a title in the first few lines
        for i, line in enumerate(lines[:5]):
            # Match markdown headings or plain text
            if match := re.match(r"^#\s+(.+)$", line):
                title = match.group(1)
                content = "\n".join(lines[i+1:])
                break
            elif line.strip() and not line.startswith("#"):
                title = line.strip()
                content = "\n".join(lines[i+1:])
                break
        
        return title, content
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract Bear tags from content."""
        # Match Bear-style tags (#tag, #tag/subtag)
        tags = re.findall(r"#([\w/]+)(?!\])", content)
        return list(set(tags))  # Remove duplicates
    
    def _process_attachments(self, content: str) -> List[Attachment]:
        """Process attachments referenced in the note."""
        attachments = []
        
        # Match Bear attachment syntax: ![name](assets/filename)
        for match in re.finditer(r"!\[(.*?)\]\((assets/[^)]+)\)", content):
            name = match.group(1) or "Untitled"
            rel_path = match.group(2)
            abs_path = self.export_path / rel_path
            
            if abs_path.exists():
                attachment = Attachment(
                    path=abs_path,
                    original_name=name,
                    content_type=self._get_content_type(abs_path),
                    metadata={"source": "bear"}
                )
                attachments.append(attachment)
        
        return attachments
    
    def _get_content_type(self, path: Path) -> str:
        """Determine content type from file extension."""
        ext = path.suffix.lower()
        content_types = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        return content_types.get(ext, "application/octet-stream") 