# Nova Import Standards

## Import Organization

All imports should be organized into the following sections, separated by a single blank line:

1. **Standard Library Imports**
   - Common utilities: `logging`, `os`, `pathlib.Path`
   - File operations: `shutil`, `io`, `mimetypes`
   - Type hints: `typing` module imports
   - Async: `asyncio`
   - Others: `traceback`, `collections`, etc.

2. **External Dependencies**
   - UI/Output: `rich.console`, `rich.table`
   - Document Processing: `PIL`, `pypdf`, `docx`
   - Image Processing: `cairosvg`, `pillow_heif`
   - Data Processing: `pandas`, `BeautifulSoup`
   - AI/ML: `openai`

3. **Internal Imports**
   - Configuration: `nova.context_processor.config.*`
   - Core functionality: `nova.context_processor.core.*`
   - Models: `nova.context_processor.models.*`
   - Handlers: `nova.context_processor.handlers.*`
   - Phases: `nova.context_processor.phases.*`
   - Utilities: `nova.context_processor.utils.*`

## Import Patterns

### Core Utilities
- `Path` from `pathlib`: Used for all path operations
- `logging`: Used for consistent logging across modules
- `os`: Used for file system operations
- `shutil`: Used for file copy/move operations
- `mimetypes`: Used in file-type specific handlers

### Type Hints
- Always import from `typing` module
- Common imports: `Dict`, `List`, `Optional`, `Union`, `Set`, `Tuple`
- Use `TYPE_CHECKING` for imports only needed for type checking
- Place type hints on a separate line from runtime imports

### External Dependencies
- Import only what's needed
- Use specific imports (e.g., `from PIL import Image` instead of `import PIL`)
- Document dependency purpose in module docstring
- Keep external dependencies minimal

### Internal Dependencies
- Use relative imports for closely related modules
- Use absolute imports for cross-module dependencies
- Avoid circular imports
- Keep dependency tree shallow

## Best Practices

1. **Import Organization**
   ```python
   """Module docstring explaining purpose and dependencies."""
   # Standard library
   import logging
   import os
   from pathlib import Path
   from typing import Dict, List, Optional

   # External dependencies
   from rich.console import Console
   from PIL import Image

   # Internal imports
   from nova.context_processor.config.manager import ConfigManager
   from nova.context_processor.core.metadata import FileMetadata
   ```

2. **Type Hint Imports**
   ```python
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from nova.context_processor.core.pipeline import NovaPipeline
   ```

3. **Handler-Specific Imports**
   ```python
   # Core utilities
   import mimetypes
   import os
   from pathlib import Path

   # Handler-specific external dependencies
   from PIL import Image

   # Internal imports
   from ..config.manager import ConfigManager
   from ..core.markdown import MarkdownWriter
   ```

4. **Phase-Specific Imports**
   ```python
   # Core utilities
   import logging
   from pathlib import Path

   # Output formatting
   from rich.console import Console
   from rich.table import Table

   # Internal imports
   from nova.context_processor.core.metadata import FileMetadata
   from nova.context_processor.phases.base import Phase
   ```

## Common Patterns by Module Type

### Handlers
- Always import `BaseHandler`
- Include file type specific imports
- Import necessary metadata models
- Import configuration manager

### Phases
- Always import `Phase` base class
- Include phase-specific utilities
- Import necessary handlers
- Import configuration and pipeline types

### Utilities
- Focus on standard library imports
- Minimize external dependencies
- Keep internal dependencies minimal

## Refactoring Guidelines

1. **Import Consolidation**
   - Group related imports
   - Remove duplicate imports
   - Use specific imports over module imports

2. **Dependency Management**
   - Document external dependencies
   - Keep dependencies up to date
   - Remove unused dependencies

3. **Type Hint Organization**
   - Separate runtime vs type checking imports
   - Use consistent type hint imports
   - Document complex type hints 