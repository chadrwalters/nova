# Nova API Reference

## Core APIs

### BearExport API

The BearExport API handles processing of Bear.app note exports, including attachments.

```python
from nova.ingestion import BearExportHandler
from nova.ingestion.types import MarkdownCorpus, Note, Attachment

# Initialize handler with export directory
handler = BearExportHandler(Path("/path/to/export"))

# Process the entire export
corpus = handler.process_export()

# Access processed notes
for note in corpus.notes:
    print(f"Note: {note.title}")
    print(f"Tags: {note.tags}")

    # Handle attachments
    for attachment in note.attachments:
        print(f"Attachment: {attachment.original_name}")
        print(f"Type: {attachment.metadata['type']}")  # 'image' or 'embed'
        print(f"Content Type: {attachment.content_type}")
```

#### BearExportHandler

Main class for processing Bear exports.

```python
class BearExportHandler:
    def __init__(self, export_path: Path):
        """Initialize with path to Bear export directory."""
        pass

    def process_export(self) -> MarkdownCorpus:
        """Process the entire export directory.

        Returns:
            MarkdownCorpus containing all processed notes with their attachments.
        """
        pass

    def _process_note(self, note_path: Path) -> Optional[Note]:
        """Process a single note file.

        Args:
            note_path: Path to the note's Markdown file.

        Returns:
            Note object if successful, None if processing failed.
        """
        pass

    def _process_attachments(self, content: str, note_dir: Path) -> List[Attachment]:
        """Process attachments referenced in note content.

        Args:
            content: Note's Markdown content.
            note_dir: Path to note's attachment directory.

        Returns:
            List of processed attachments.
        """
        pass
```

#### Types

```python
@dataclass
class Note:
    title: str
    content: str
    path: Path
    created_at: datetime
    modified_at: datetime
    tags: List[str]
    attachments: List[Attachment]
    metadata: Dict[str, Any]

@dataclass
class Attachment:
    path: Path
    original_name: str
    content_type: str
    metadata: Dict[str, Any]

@dataclass
class MarkdownCorpus:
    notes: List[Note]
    root_path: Path
    metadata: Dict[str, Any]
```

### Processing API

```python
from nova.processing.chunking import ChunkingEngine
from nova.processing import EmbeddingService
from nova.processing.vector_store import VectorStore
from nova.ephemeral import EphemeralManager
from nova.types import Document, Chunk

# Initialize components
chunker = ChunkingEngine()
embedder = EmbeddingService()
persistent_store = VectorStore()
ephemeral_manager = EphemeralManager()

# Process document
chunks = chunker.chunk_document(
    document,
    chunk_size=500,
    heading_weight=1.5
)

# Handle persistent data
persistent_embeddings = embedder.embed_chunks(chunks)
persistent_store.add_chunks(chunks, persistent_embeddings)

# Handle ephemeral data
ephemeral_chunks = [c for c in chunks if c.is_ephemeral]
ephemeral_embeddings = embedder.embed_chunks(ephemeral_chunks)
for chunk, embedding in zip(ephemeral_chunks, ephemeral_embeddings):
    ephemeral_manager.add_data(
        content=chunk.content,
        metadata=chunk.metadata,
        embedding=embedding,
        ttl=300  # 5 minutes
    )

# Search (now searches both stores)
results = orchestrator.process_query("search query", k=5)
```

### RAG API

```python
from nova.rag import RAGOrchestrator
from nova.types import MCPPayload

# Initialize components
vector_store = VectorStore(embedding_dim=384)
ephemeral_manager = EphemeralManager(
    embedding_dim=384,
    default_ttl=300,  # 5 minutes
    cleanup_interval=60  # Check expiry every minute
)
embedding_svc = EmbeddingService(model_name="all-MiniLM-L6-v2")

# Initialize orchestrator with both stores
orchestrator = RAGOrchestrator(
    vector_store=vector_store,
    ephemeral_manager=ephemeral_manager,
    embedding_service=embedding_svc,
    top_k=5
)

# Process query (async)
async def process_query():
    response = await orchestrator.process_query("What did we decide about Project X?")
    print(response.content)

# Process streaming query (async)
async def process_streaming_query():
    async for chunk in orchestrator.process_query_streaming("What did we decide about Project X?"):
        print(chunk, end="", flush=True)

# Run with asyncio
import asyncio
asyncio.run(process_query())
```

### Claude API

```python
from nova.llm import ClaudeClient
from nova.types import MCPPayload, ClaudeResponse
from anthropic import RateLimitError, APIError

# Initialize client
client = ClaudeClient(
    api_key="your_key_here",
    model="claude-2",
    max_tokens=1000,
    temperature=0.7
)

# Complete prompt (async)
async def get_completion():
    try:
        response = await client.complete(
            mcp_payload=mcp_payload,
            stream=False
        )
        print(response.content)
    except RateLimitError:
        # Automatic retry after 1s
        print("Rate limited, retrying...")
    except APIError as e:
        print(f"API error: {e}")

# Stream completion (async)
async def stream_completion():
    try:
        async for chunk in await client.complete(
            mcp_payload=mcp_payload,
            stream=True
        ):
            print(chunk, end="", flush=True)
    except RateLimitError:
        # Automatic retry after 1s
        print("Rate limited, retrying...")
    except APIError as e:
        print(f"API error: {e}")

# Run with asyncio
import asyncio
asyncio.run(get_completion())
```

## Configuration API

```python
from nova.config import NovaConfig
from pathlib import Path

# Load config
config = NovaConfig.from_yaml(Path("nova.yaml"))

# Access settings
chunk_size = config.ingestion.chunk_size
model_name = config.embedding.model
```

## Error Handling

```python
from nova.errors import (
    ConversionError,
    EmbeddingError,
    LLMError,
    EphemeralDataError
)

try:
    result = converter.convert_file(file_path)
except ConversionError as e:
    logger.error(f"Conversion failed: {e.message}")
    placeholder = converter.handle_conversion_failure(file_path)
```

## Utility Functions

```python
from nova.utils import (
    sanitize_content,
    validate_api_key,
    setup_logging
)

# Content sanitization
safe_content = sanitize_content(raw_content)

# API key validation
is_valid = validate_api_key(api_key)

# Logging setup
logger = setup_logging(
    log_level="INFO",
    log_file="nova.log"
)
```

## Type Definitions

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np

@dataclass
class Document:
    content: str
    metadata: dict
    source_path: Path

@dataclass
class Chunk:
    content: str
    metadata: dict
    embedding: Optional[np.ndarray] = None
    is_ephemeral: bool = False

@dataclass
class MCPPayload:
    system_instructions: str
    developer_instructions: str
    user_message: str
    context_blocks: list[ContextBlock]

@dataclass
class ContextBlock:
    content: str
    metadata: dict
    ephemeral: bool = False
```

## Command Line Interface

```bash
# Basic usage
nova process-export /path/to/export

# With custom config
nova --config custom.yaml process-export /path/to/export

# Query mode
nova query "What did we decide about Project X?"

# Cloud mode
nova --cloud query "What did we decide about Project X?"
```
