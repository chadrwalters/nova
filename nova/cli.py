import argparse
from pathlib import Path
import sys
from typing import Optional

from nova.utils.config import NovaConfig
from nova.ingestion import BearExportHandler
from nova.processing import ChunkingEngine, EmbeddingService
from nova.rag import RAGOrchestrator
from nova.llm import ClaudeClient
from nova.vector_store import VectorStore
from nova.ephemeral_store import EphemeralVectorStore


def setup_ingestion(args, config: NovaConfig) -> int:
    """Handle data ingestion commands"""
    try:
        handler = BearExportHandler(Path(args.input_path))
        corpus = handler.process_export()
        print(f"Successfully processed Bear export from {args.input_path}")
        return 0
    except Exception as e:
        print(f"Error during ingestion: {e}", file=sys.stderr)
        return 1


def process_documents(args, config: NovaConfig) -> int:
    """Handle document processing commands"""
    try:
        chunker = ChunkingEngine(
            chunk_size=config.ingestion.chunk_size,
            heading_weight=config.ingestion.heading_weight
        )
        embedding_svc = EmbeddingService(
            model_name=config.embedding.model
        )
        
        # Process documents and generate embeddings
        chunks = chunker.process_directory(Path(args.input_path))
        embedding_svc.embed_chunks(chunks)
        
        print(f"Successfully processed documents from {args.input_path}")
        return 0
    except Exception as e:
        print(f"Error during processing: {e}", file=sys.stderr)
        return 1


def query_knowledge(args, config: NovaConfig) -> int:
    """Handle knowledge base queries"""
    try:
        # Validate LLM config before querying
        config.llm.validate()
        
        # Initialize components
        vector_store = VectorStore(embedding_dim=config.embedding.dimension)
        ephemeral_store = EphemeralVectorStore(embedding_dim=config.embedding.dimension)
        embedding_svc = EmbeddingService(model_name=config.embedding.model)
        
        rag = RAGOrchestrator(
            vector_store=vector_store,
            ephemeral_store=ephemeral_store,
            embedding_service=embedding_svc,
            top_k=config.rag.top_k
        )
        
        claude = ClaudeClient(
            api_key=config.llm.api_key or "",  # validate() ensures this is not None
            model=config.llm.model,
            max_tokens=config.llm.max_tokens
        )
        
        # Get response (stream if requested)
        if args.stream:
            async def stream_response():
                async for chunk in rag.process_query_streaming(args.query):
                    print(chunk, end="", flush=True)
                print()  # Final newline
            import asyncio
            asyncio.run(stream_response())
        else:
            import asyncio
            async def get_response():
                response = await rag.process_query(args.query)
                print(response.content)
            asyncio.run(get_response())
            
        return 0
    except Exception as e:
        print(f"Error during query: {e}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Nova - Personal Knowledge Management System")
    parser.add_argument(
        "--config",
        type=str,
        default="config/nova.yaml",
        help="Path to configuration file",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Ingestion command
    ingest_parser = subparsers.add_parser("ingest", help="Import data into Nova")
    ingest_parser.add_argument("input_path", type=str, help="Path to Bear export")
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process documents")
    process_parser.add_argument("input_path", type=str, help="Path to documents directory")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query the knowledge base")
    query_parser.add_argument("query", type=str, help="Query string")
    query_parser.add_argument("--stream", action="store_true", help="Stream the response")
    
    args = parser.parse_args()

    try:
        config = NovaConfig.from_yaml(Path(args.config))
        
        if args.command == "ingest":
            return setup_ingestion(args, config)
        elif args.command == "process":
            return process_documents(args, config)
        elif args.command == "query":
            return query_knowledge(args, config)
        else:
            print("Please specify a command. Use --help for usage information.")
            return 1
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 