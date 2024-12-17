import click
import asyncio
from pathlib import Path
import os
from dotenv import load_dotenv

from src.pipeline import Pipeline

@click.group()
def cli():
    """Nova document processing CLI."""
    pass

@cli.command()
def process():
    """Process markdown files to PDF."""
    # Load environment variables
    load_dotenv()
    
    # Get directories from environment
    input_dir = Path(os.getenv('NOVA_INPUT_DIR'))
    output_dir = Path(os.getenv('NOVA_OUTPUT_DIR'))
    
    # Create and run pipeline
    pipeline = Pipeline(input_dir, output_dir)
    asyncio.run(pipeline.run())

if __name__ == '__main__':
    cli()
