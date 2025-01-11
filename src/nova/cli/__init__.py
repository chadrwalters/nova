"""Nova CLI module."""

import asyncio
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional, AsyncGenerator

import click
import nest_asyncio
import numpy as np
from nova.config import NovaConfig
from nova.ingestion.bear import BearExportHandler
from nova.rag import RAGOrchestrator
from nova.processing import EmbeddingService
from nova.processing.vector_store import VectorStore
from nova.ephemeral import EphemeralManager
from nova.types import Chunk

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Global components
embedding_service: Optional[EmbeddingService] = None
vector_store: Optional[VectorStore] = None
ephemeral_manager: Optional[EphemeralManager] = None


def init_components(config_obj):
    global embedding_service, vector_store, ephemeral_manager

    if embedding_service is None:
        embedding_service = EmbeddingService()

    if vector_store is None:
        vector_store = VectorStore(embedding_dim=384)
        vector_store_dir = Path("_Nova") / "vector_store"
        config_file = vector_store_dir / "config.json"
        if config_file.exists():
            vector_store.load(vector_store_dir)

    if ephemeral_manager is None:
        ephemeral_manager = EphemeralManager()


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run an async function in the current event loop or create a new one."""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


@click.group()
def cli() -> None:
    """Nova CLI for processing and querying documents."""
    pass


@cli.command("query")
@click.argument("query_text")
@click.option("--config", default="config/nova.yaml", help="Path to config file")
def query(query_text: str, config: str) -> None:
    """Query the knowledge base."""
    config_obj = NovaConfig.from_yaml(config)
    init_components(config_obj)

    # Initialize orchestrator with global components
    orchestrator = RAGOrchestrator(
        vector_store=vector_store,
        ephemeral_manager=ephemeral_manager,
        embedding_service=embedding_service,
        top_k=5
    )

    # Process query
    response = asyncio.run(process_query(query_text, orchestrator))
    click.echo(f"\nQuery: {query_text}")
    click.echo(f"Response: {response}")


@cli.command("process-export")
@click.argument("export_path")
@click.option("--config", default="config/nova.yaml", help="Path to config file")
def process_export(export_path: str, config: str) -> None:
    """Process a Bear export directory."""
    config_obj = NovaConfig.from_yaml(config)
    init_components(config_obj)

    handler = BearExportHandler(Path(export_path))
    corpus = handler.process_export()

    # Process each note into chunks and add to vector store
    for note in corpus.notes:
        chunk = Chunk(
            content=note.content,
            metadata={
                "title": note.title,
                "path": str(note.path),
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "modified_at": note.modified_at.isoformat() if note.modified_at else None,
                "tags": note.tags
            }
        )
        embeddings = asyncio.run(embedding_service.embed_chunks([chunk]))
        vector_store.add_chunks([chunk], np.array(embeddings))

    # Save vector store state
    vector_store_dir = Path("_Nova") / "vector_store"
    vector_store_dir.mkdir(parents=True, exist_ok=True)
    vector_store.save(vector_store_dir)

    click.echo(f"\nProcessed {len(corpus.notes)} notes from {export_path}")
    click.echo("\nDetailed breakdown:")

    for note in corpus.notes:
        click.echo(f"\n📝 Note: {note.title}")
        click.echo(f"  📍 Path: {note.path}")
        if note.tags:
            click.echo(f"  🏷️  Tags: {', '.join(note.tags)}")
        if note.attachments:
            click.echo(f"  📎 Attachments ({len(note.attachments)}):")
            for att in note.attachments:
                click.echo(f"    - {att.original_name} ({att.content_type})")
                click.echo(f"      Path: {att.path}")
                click.echo(f"      Type: {att.metadata.get('type', 'unknown')}")
        click.echo(f"  📅 Modified: {note.modified_at}")


async def process_query(query: str, orchestrator: RAGOrchestrator) -> str:
    """Process a query using the RAG orchestrator."""
    response = await orchestrator.process_query(query)
    return response


async def process_query_stream(query: str, orchestrator: RAGOrchestrator) -> AsyncGenerator[str, None]:
    """Process a streaming query using the RAG orchestrator."""
    async for chunk in orchestrator.process_query_streaming(query):
        yield chunk


@cli.command()
@click.argument("config")
def validate_config(config: str) -> None:
    """Validate configuration file."""
    from nova.utils import validate_config as validate

    try:
        validate(config)
        click.echo("Config validation successful")
    except Exception as e:
        click.echo(f"Config validation failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--backup-dir",
    type=click.Path(path_type=Path),
    help="Backup directory"
)
@click.pass_context
def backup(ctx: click.Context, backup_dir: Optional[Path]) -> None:
    """Create a backup of Nova data."""
    from nova.utils import create_backup

    try:
        backup_path = create_backup(backup_dir)
        click.echo(f"Backup created at {backup_path}")
    except Exception as e:
        click.echo(f"Backup failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--backup-dir",
    type=click.Path(exists=True, path_type=Path),
    help="Backup directory"
)
@click.pass_context
def restore(ctx: click.Context, backup_dir: Path) -> None:
    """Restore Nova data from backup."""
    from nova.utils import restore_backup

    try:
        restore_backup(backup_dir)
        click.echo("Restore completed successfully")
    except Exception as e:
        click.echo(f"Restore failed: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
