#!/usr/bin/env python3
"""CLI module to process text into vectors using the Nova vector store."""
import logging
from pathlib import Path
import asyncio
import click
import numpy as np

from nova.vector_store.chunking import ChunkingEngine
from nova.vector_store.embedding import EmbeddingEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def process_text(text: str, output_dir: Path) -> None:
    """Process a text document into vectors."""
    try:
        # Initialize engines
        chunking_engine = ChunkingEngine()
        embedding_engine = EmbeddingEngine()

        # Process text into chunks
        chunks = chunking_engine.chunk_document(text, "cli_input")
        logger.info(f"Generated {len(chunks)} chunks from text")

        # Generate embeddings
        embeddings = embedding_engine.embed_texts([chunk.content for chunk in chunks])
        logger.info(f"Generated {len(embeddings)} embeddings")

        # Save results
        output_dir.mkdir(parents=True, exist_ok=True)
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_file = output_dir / f"chunk_{i}.txt"
            embedding_file = output_dir / f"embedding_{i}.npy"

            # Save chunk text
            chunk_file.write_text(chunk.content)

            # Save embedding
            np.save(embedding_file, embedding.embedding)

        logger.info(f"Saved results to {output_dir}")

    except Exception as e:
        logger.error(f"Error processing text: {e}")
        raise


@click.command()
@click.argument("text", type=str)
@click.argument("output_dir", type=click.Path())
def main(text: str, output_dir: str) -> None:
    """Process text into vectors."""
    asyncio.run(process_text(text, Path(output_dir)))


if __name__ == "__main__":
    main()
