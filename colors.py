from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "success": "green",
    "header": "blue bold",
    "processing": "magenta",
    "path": "cyan",
    "number": "yellow",
})

console = Console(theme=custom_theme)

class Colors:
    @staticmethod
    def header(text: str) -> None:
        console.print(f"[header]{text}[/]")
    
    @staticmethod
    def success(text: str) -> None:
        console.print(f"[success]✓ {text}[/]")
    
    @staticmethod
    def warning(text: str) -> None:
        console.print(f"[warning]⚠️  {text}[/]")
    
    @staticmethod
    def error(text: str) -> None:
        console.print(f"[error]✗ {text}[/]")
    
    @staticmethod
    def info(text: str) -> None:
        console.print(f"[info]{text}[/]")
    
    @staticmethod
    def processing(text: str) -> None:
        console.print(f"[processing]{text}[/]")
    
    @staticmethod
    def path(text: str) -> None:
        console.print(f"[path]{text}[/]")

    @staticmethod
    def divider() -> None:
        console.print("[blue]" + "━" * 70 + "[/]")