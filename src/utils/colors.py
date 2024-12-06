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
    def __init__(self):
        """Initialize the console with rich formatting."""
        self.console = Console(theme=NOVA_THEME)
    
    def section(self, text: str) -> None:
        """Print a section header with consistent styling."""
        self.console.print()
        self.console.rule(f"[header]{text}[/]", style="divider", align="center")
        self.console.print()
    
    def header(self, text: str) -> None:
        """Print a section header with consistent spacing."""
        self.section(text)
    
    def process_start(self, process: str, details: Optional[str] = None) -> None:
        """Print process start message with consistent formatting."""
        self.console.print()
        msg = f"[info]►[/] Starting [bright_white]{process}[/]"
        if details:
            msg += f"\n  [path]{self._normalize_path(details)}[/]"
        self.console.print(msg)
    
    def process_item(self, item: str) -> None:
        """Print item processing message."""
        self.console.print(f"[info]ℹ[/] Processing: [path]{self._normalize_path(item)}[/]")
    
    def warning(self, text: str) -> None:
        """Print warning message."""
        self.console.print(f"[warning]⚠[/] {text}")
    
    def error(self, title: str, details: Optional[str] = None) -> None:
        """Print error message with optional details."""
        self.console.print(f"[error]✗[/] {title}")
        if details:
            self.console.print(f"  [detail]{details}[/]")
    
    def success(self, title: str, details: str = "") -> None:
        """Print a success message with optional details."""
        self.console.print(f"[success]✓[/] {title}")
        if details:
            for line in details.split('\n'):
                self.console.print(f"  [value]{line}[/]")
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for display."""
        return str(Path(path).expanduser())