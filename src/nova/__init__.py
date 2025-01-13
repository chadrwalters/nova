"""Nova - A RAG-based system for Bear.app notes with MCP integration."""

__version__ = "0.1.0"

from . import config, monitoring, rag, vector_store

__all__ = ["config", "vector_store", "rag", "monitoring"]
