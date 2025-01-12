#!/usr/bin/env python3
"""CLI module to process Bear notes into vectors using the Nova vector
store."""
import logging
from pathlib import Path
import asyncio
import click
import numpy as np

from nova.bear_parser.parser import BearParser
from nova.vector_store.chunking import ChunkingEngine
from nova.vector_store.embedding import EmbeddingEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def process_notes(notes_dir: Path, output_dir: Path) -> None:
    """Process Bear notes into vectors."""
    try:
        # Initialize components
        parser = BearParser(notes_dir)
        chunking_engine = ChunkingEngine()
        embedding_engine = EmbeddingEngine()

        # Parse Bear notes
        notes = await parser.parse_directory()
        logger.info(f"Parsed {len(notes)} notes from {notes_dir}")

        # Process each note
        for note in notes:
            try:
                # Create note-specific output directory
                note_dir = output_dir / note.title.replace(" ", "_")
                note_dir.mkdir(parents=True, exist_ok=True)

                # Process note content into chunks
                chunks = chunking_engine.chunk_document(
                    note.content, f"note:{note.title}", list(note.tags)
                )
                logger.info(f"Generated {len(chunks)} chunks from note: {note.title}")

                # Generate embeddings
                embeddings = embedding_engine.embed_texts(
                    [chunk.content for chunk in chunks]
                )
                logger.info(
                    f"Generated {len(embeddings)} embeddings for note: {note.title}"
                )

                # Save results
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    chunk_file = note_dir / f"chunk_{i}.txt"
                    embedding_file = note_dir / f"embedding_{i}.npy"

                    # Save chunk text
                    chunk_file.write_text(chunk.content)

                    # Save embedding
                    np.save(embedding_file, embedding.embedding)

                logger.info(f"Saved results for note: {note.title}")

            except Exception as e:
                logger.error(f"Error processing note {note.title}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error processing notes: {e}")
        raise


@click.command()
@click.argument("notes_dir", type=click.Path(exists=True))
@click.argument("output_dir", type=click.Path())
def main(notes_dir: str, output_dir: str) -> None:
    """Process Bear notes into vectors."""
    asyncio.run(process_notes(Path(notes_dir), Path(output_dir)))


if __name__ == "__main__":
    main()
