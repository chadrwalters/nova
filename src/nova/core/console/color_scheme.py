"""Color scheme management for Nova console output."""

from typing import Dict, Optional, Union
from rich.style import Style
from rich.theme import Theme
from rich.console import Console
import os

class ColorScheme:
    """Color scheme for console output."""
    
    # Base colors with fallbacks
    COLORS = {
        'black': {'ansi': '\033[30m', 'hex': '#000000', 'fallback': 'dim'},
        'white': {'ansi': '\033[37m', 'hex': '#FFFFFF', 'fallback': 'bright'},
        'red': {'ansi': '\033[31m', 'hex': '#FF0000', 'fallback': 'bold'},
        'green': {'ansi': '\033[32m', 'hex': '#00FF00', 'fallback': 'bold'},
        'blue': {'ansi': '\033[34m', 'hex': '#0000FF', 'fallback': 'bold'},
        'yellow': {'ansi': '\033[33m', 'hex': '#FFFF00', 'fallback': 'bold'},
        'magenta': {'ansi': '\033[35m', 'hex': '#FF00FF', 'fallback': 'bold'},
        'cyan': {'ansi': '\033[36m', 'hex': '#00FFFF', 'fallback': 'bold'}
    }
    
    # Style definitions with fallbacks
    STYLES = {
        # Log levels
        'debug': Style(color="cyan", dim=True),
        'info': Style(color="blue"),
        'warning': Style(color="yellow"),
        'error': Style(color="red"),
        'critical': Style(color="red", bold=True),
        
        # Progress and status
        'success': Style(color="green"),
        'failure': Style(color="red"),
        'pending': Style(color="yellow"),
        'skipped': Style(dim=True),
        
        # Tables
        'header': Style(color="blue", bold=True),
        'border': Style(color="blue", dim=True),
        'title': Style(color="blue", bold=True),
        'row': Style(color="white"),
        'alternate_row': Style(color="white", dim=True),
        
        # Progress bars
        'bar': Style(color="blue"),
        'bar_complete': Style(color="green"),
        'bar_finished': Style(color="green", bold=True),
        'spinner': Style(color="cyan"),
        'progress_text': Style(color="white"),
        
        # Timestamps and metadata
        'time': Style(dim=True),
        'metadata': Style(color="cyan", dim=True),
        'path': Style(color="cyan"),
        'file': Style(color="cyan", underline=True),
        'directory': Style(color="blue", bold=True),
        
        # Special formatting
        'highlight': Style(color="magenta", bold=True),
        'dim': Style(dim=True),
        'bold': Style(bold=True),
        'italic': Style(italic=True),
        'url': Style(color="blue", underline=True),
        'code': Style(color="magenta", dim=True),
        'quote': Style(italic=True, dim=True)
    }
    
    # Rich console features
    FEATURES = {
        'syntax_highlighting': True,
        'markdown_rendering': True,
        'emoji_support': True,
        'hyperlinks': True,
        'progress_bars': True
    }
    
    @classmethod
    def detect_terminal_capabilities(cls) -> Dict[str, bool]:
        """Detect terminal capabilities."""
        console = Console()
        return {
            'color': console.color_system is not None,
            'unicode': console.encoding == "utf-8",
            'interactive': console.is_interactive,
            'terminal': console.is_terminal,
            'legacy': os.environ.get('TERM') in ['dumb', 'unknown'],
            'width': console.width,
            'height': console.height
        }
    
    @classmethod
    def get_color_hex(cls, color: str) -> str:
        """Get hex code for a color name."""
        return cls.COLORS.get(color, {}).get('hex', color)
    
    @classmethod
    def get_color_ansi(cls, color: str) -> str:
        """Get ANSI code for a color name."""
        return cls.COLORS.get(color, {}).get('ansi', '')
    
    @classmethod
    def get_style(cls, style_name: str, fallback: bool = False) -> Optional[Style]:
        """Get a style by name with optional fallback."""
        style = cls.STYLES.get(style_name)
        if not style and fallback:
            # Create basic fallback style
            return Style(bold=True if 'bold' in style_name else False,
                       dim=True if 'dim' in style_name else False,
                       italic=True if 'italic' in style_name else False)
        return style
    
    @classmethod
    def apply(cls, text: str, style_name: str, fallback: bool = True) -> str:
        """Apply a style to text with fallback support."""
        capabilities = cls.detect_terminal_capabilities()
        
        if capabilities['color']:
            if style := cls.get_style(style_name, fallback):
                return f"[{style}]{text}[/]"
        else:
            # Use ANSI fallback if available
            color = style_name.split()[0]
            if ansi := cls.get_color_ansi(color):
                return f"{ansi}{text}\033[0m"
            
        return text
    
    @classmethod
    def get_theme(cls) -> Theme:
        """Get a rich theme from the color scheme."""
        return Theme({name: style for name, style in cls.STYLES.items()})
    
    @classmethod
    def configure_console(cls, console: Console) -> None:
        """Configure a rich console with our color scheme and features."""
        capabilities = cls.detect_terminal_capabilities()
        
        # Apply theme
        console.theme = cls.get_theme()
        
        # Configure features based on capabilities
        console.no_color = not capabilities['color']
        console.soft_wrap = True
        console.record = True
        
        # Set width for non-terminal environments
        if not capabilities['terminal']:
            console.width = 100
            
        # Configure markup and emoji based on Unicode support
        console.markup = capabilities['unicode']
        console.emoji = capabilities['unicode'] and cls.FEATURES['emoji_support']
        
        # Configure other features
        console.highlight = cls.FEATURES['syntax_highlighting']
        console.hyperlinks = capabilities['terminal'] and cls.FEATURES['hyperlinks'] 