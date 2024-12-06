from rich.theme import Theme
from rich.console import Console
from rich.rule import Rule
from typing import Optional, Dict, Any
from pathlib import Path

NOVA_THEME = Theme({
    'info': 'blue',
    'success': 'green',
    'warning': 'yellow',
    'error': 'red',
    'header': 'bold white',
    'divider': 'blue',
    'path': 'cyan',
    'stats': 'bold white',
    'value': 'white',
    'detail': 'dim white'
})

class NovaConsole:
    """Console wrapper for consistent styling."""
    
    def __init__(self):
        """Initialize the console with Nova theme."""
        self.console = Console(theme=NOVA_THEME)
        
    def process_start(self, name: str, detail: Optional[str] = None) -> None:
        """Start a process with a header."""
        self.console.print(f"\n► Starting {name}", style="header")
        if detail:
            self.console.print(f"  {detail}", style="detail")
            
    def process_item(self, message: str) -> None:
        """Print a process item."""
        self.console.print(f"  {message}", style="value")
        
    def process_end(self, message: str) -> None:
        """End a process with a success message."""
        self.console.print(f"✓ {message}", style="success")
        
    def error(self, message: str, detail: Optional[str] = None) -> None:
        """Print an error message."""
        self.console.print(f"✗ {message}", style="error")
        if detail:
            self.console.print(f"  {detail}", style="detail")
            
    def success(self, message: str, detail: Optional[str] = None) -> None:
        """Print a success message."""
        self.console.print(f"✓ {message}", style="success")
        if detail:
            self.console.print(f"  {detail}", style="detail")
            
    def warning(self, message: str, detail: Optional[str] = None) -> None:
        """Print a warning message."""
        self.console.print(f"! {message}", style="warning")
        if detail:
            self.console.print(f"  {detail}", style="detail")
    
    def section(self, text: str) -> None:
        """Print a section header with consistent styling."""
        self.console.print()
        self.console.rule(f"[header]{text}[/]", style="divider", align="center")
        self.console.print()
    
    def header(self, text: str) -> None:
        """Print a section header with consistent spacing."""
        self.section(text)
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for display."""
        return str(Path(path).expanduser())