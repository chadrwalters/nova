# Nova API Reference

## Core APIs

### BearExport API

```python
from nova.ingestion import BearExportHandler, DoclingConverter
from nova.types import MarkdownCorpus, ConversionResult

# Initialize handlers
export_handler = BearExportHandler()
converter = DoclingConverter()

# Process Bear export
corpus = export_handler.process_export("/path/to/export")

# Convert attachments
for attachment in corpus.attachments:
    result = converter.convert_file(attachment.path)
    if not result.success:
        placeholder = converter.handle_conversion_failure(attachment.path)
```

### Processing API

```python
from nova.processing import (
    ChunkingEngine, 
    EmbeddingService, 
    VectorStore,
    EphemeralVectorStore
)
from nova.types import Document, Chunk

# Initialize components
chunker = ChunkingEngine()
embedder = EmbeddingService()
persistent_store = VectorStore()
ephemeral_store = EphemeralVectorStore()

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
ephemeral_store.add_chunks(ephemeral_chunks, ephemeral_embeddings)

# Search (now searches both stores)
results = orchestrator.process_query("search query", k=5)
```

### RAG API

```python
from nova.rag import RAGOrchestrator
from nova.types import MCPPayload

# Initialize components
vector_store = VectorStore(embedding_dim=384)
ephemeral_store = EphemeralVectorStore(embedding_dim=384)
embedding_svc = EmbeddingService(model_name="all-MiniLM-L6-v2")

# Initialize orchestrator with both stores
orchestrator = RAGOrchestrator(
    vector_store=vector_store,
    ephemeral_store=ephemeral_store,
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

# Initialize client
client = ClaudeClient(
    api_key="your_key_here",
    model="claude-2",
    max_tokens=1000,
    temperature=0.7
)

# Complete prompt (async)
async def get_completion():
    response = await client.complete(
        mcp_payload=mcp_payload,
        stream=False
    )
    print(response.content)

# Stream completion (async)
async def stream_completion():
    async for chunk in await client.complete(
        mcp_payload=mcp_payload,
        stream=True
    ):
        print(chunk, end="", flush=True)

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