import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from nova.ingestion.types import Attachment

@dataclass
class ConversionResult:
    success: bool
    text: Optional[str] = None
    error: Optional[str] = None

class DoclingConverter:
    def __init__(self):
        """Initialize the Docling converter."""
        pass
    
    def convert_attachment(self, attachment: Attachment) -> bool:
        """Convert an attachment to text using Docling CLI."""
        try:
            # Run docling convert command
            result = subprocess.run(
                ["docling", "convert", str(attachment.path), "--format", "text"],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.returncode == 0 and result.stdout:
                attachment.converted_text = result.stdout.strip()
                attachment.metadata.update({
                    "conversion_success": "true",
                    "converter": "docling"
                })
                return True
            else:
                return self._handle_conversion_failure(
                    attachment,
                    ConversionResult(success=False, error="No text extracted")
                )
        except subprocess.CalledProcessError as e:
            print(f"Error converting {attachment.path}: {e.stderr}")
            return self._handle_conversion_failure(
                attachment,
                ConversionResult(success=False, error=e.stderr)
            )
        except Exception as e:
            print(f"Error converting {attachment.path}: {e}")
            return self._handle_conversion_failure(
                attachment,
                ConversionResult(success=False, error=str(e))
            )
    
    def _handle_conversion_failure(
        self, 
        attachment: Attachment, 
        result: Optional[ConversionResult] = None
    ) -> bool:
        """Handle conversion failures and create placeholders."""
        attachment.metadata.update({
            "conversion_success": "false",
            "converter": "docling"
        })
        
        if result and result.error:
            attachment.metadata["error"] = result.error
        
        # Create a placeholder text based on file type
        if attachment.content_type.startswith("image/"):
            attachment.converted_text = f"[Image: {attachment.original_name}]"
        else:
            attachment.converted_text = f"[Document: {attachment.original_name}]"
        
        return False 