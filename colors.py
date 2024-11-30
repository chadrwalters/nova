from rich.theme import Theme
from rich.console import Console
from rich.status import Status
from rich.rule import Rule
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

NOVA_THEME = Theme({
    'info': 'bright_cyan',
    'success': 'bright_green',
    'warning': 'bright_yellow',
    'error': 'bright_red',
    'header': 'bold white',
    'label': 'bright_blue',
    'path': 'bright_cyan',
    'stats': 'dim white',
    'value': 'bright_white',
    'divider': 'dim cyan',
    'process': 'bright_magenta'
})

class NovaConsole:
    def __init__(self):
        self.console = Console(theme=NOVA_THEME)
        
    def header(self, text: str) -> None:
        """Print a section header with consistent spacing."""
        self.console.print()
        self.console.rule(f"[header]{text}[/]", style="divider")
        self.console.print()
        
    def process_start(self, process: str, details: Optional[str] = None) -> None:
        """Print process start message."""
        msg = f"[info]ℹ[/] Starting [bright_cyan]{process}[/]"
        if details:
            msg += f"\n  [path]{self._normalize_path(details)}[/]"
        self.console.print(msg)
        
    def process_item(self, item: str) -> None:
        """Print item processing message."""
        self.console.print(f"[info]ℹ[/] Processing: [path]{self._normalize_path(item)}[/]")
        
    def process_complete(self, process: str, stats: Optional[Dict[str, Any]] = None) -> None:
        """Print process completion message with optional statistics."""
        self.console.print(f"[success]✓[/] {process} complete")
        if stats:
            for key, value in stats.items():
                if 'path' in key.lower() or 'file' in key.lower() or 'output' in key.lower():
                    value = self._normalize_path(str(value))
                    self.console.print(f"  [detail]{key}:[/] [path]{value}[/]")
                else:
                    self.console.print(f"  [detail]{key}:[/] {value}")
        self.console.print()  # Add spacing after stats
        
    def success(self, text: str) -> None:
        """Print success message."""
        self.console.print(f"[success]✓[/] {text}")
        
    def warning(self, text: str) -> None:
        """Print warning message."""
        self.console.print(f"[warning]⚠[/] {text}")
        
    def error(self, text: str, details: Optional[str] = None) -> None:
        """Print error message with optional details."""
        self.console.print(f"[error]✗[/] {text}")
        if details:
            self.console.print(f"  [detail]{details}[/]")
            
    def _normalize_path(self, path: str) -> str:
        """Normalize path for display."""
        return str(Path(path).expanduser())