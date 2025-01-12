"""Nova - A RAG-based system for Bear.app notes with MCP integration."""

__version__ = "0.1.0"

from . import config
from . import ingestion
from . import vector_store
from . import rag
from . import monitoring

__all__ = ["config", "ingestion", "vector_store", "rag", "monitoring"]
