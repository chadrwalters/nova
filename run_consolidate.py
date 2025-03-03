#!/usr/bin/env python
"""
Simple wrapper script to run the consolidate-markdown command with the existing configuration.
"""

import asyncio
import subprocess
import sys


async def main():
    """Run the consolidate-markdown command."""
    config_path = "config/consolidate-markdown.toml"

    print(f"Running consolidate-markdown with config: {config_path}")

    # Run the consolidate-markdown command
    process = subprocess.run(
        ["uv", "run", "consolidate-markdown", "--config", config_path],
        capture_output=False,
        text=True,
        check=False,
    )

    return process.returncode


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
