#!/usr/bin/env python3
"""
Script to update Python import paths after moving code from src/nova to src/nova/context_processor.

Usage:
  python update_imports.py [--apply]

By default, the script will do a dry run and only print changes.
Pass --apply to actually write the changes to disk.
"""

import argparse
import os
import re
from pathlib import Path

def update_paths_in_file(file_path: Path, apply: bool = False) -> bool:
    """
    Update imports or references within a Python file from:
      'src/nova/...'
    to:
      'src/nova/context_processor/...'
    or the equivalent import statements such as 'from nova import X' => 'from nova.context_processor import X'

    Returns True if any changes were made, False otherwise.
    """
    if not file_path.is_file():
        return False

    # We only care about .py files or possibly .md, .yaml, etc. if references to 'src/nova' exist
    if file_path.suffix.lower() not in (".py", ".md", ".yaml", ".yml", ".txt", ".rst"):
        return False

    # Skip files that are already in the context_processor directory
    if "context_processor" in str(file_path):
        return False

    original_text = file_path.read_text(encoding="utf-8")
    updated_text = original_text

    # Regex #1: "from nova..." => "from nova.context_processor..."
    # We have to watch for lines like:
    #   from nova import x
    #   from nova.something import y
    #   from nova.something.more import z
    pattern_from_nova = re.compile(r'(\bfrom\s+nova)(\.[a-zA-Z0-9_.]+)?(\s+import\s+)')

    def _repl_from_nova(m):
        g1, g2, g3 = m.group(1), m.group(2), m.group(3)
        if g2 is None:
            return f"{g1}.context_processor{g3}"
        else:
            return f"{g1}.context_processor{g2}{g3}"

    updated_text = pattern_from_nova.sub(_repl_from_nova, updated_text)

    # Regex #2: "import nova.something" => "import nova.context_processor.something"
    pattern_import_nova = re.compile(r'(\bimport\s+nova)(\.[a-zA-Z0-9_.]+)')

    def _repl_import_nova(m):
        return f"{m.group(1)}.context_processor{m.group(2)}"

    updated_text = pattern_import_nova.sub(_repl_import_nova, updated_text)

    # Regex #3: references to "nova/" or "nova\" in strings
    updated_text = re.sub(r'(?<!context_processor/)nova/', 'nova/context_processor/', updated_text)
    updated_text = re.sub(r'(?<!context_processor\\)nova\\', r'nova\\context_processor\\', updated_text)

    # If no changes made, bail out
    if updated_text == original_text:
        return False

    if apply:
        file_path.write_text(updated_text, encoding="utf-8")
    else:
        # Just print the diff or a summary
        print(f"\n--- Changes in {file_path} ---")
        old_lines = original_text.splitlines()
        new_lines = updated_text.splitlines()
        from difflib import unified_diff
        diff = unified_diff(old_lines, new_lines, fromfile=str(file_path), tofile=str(file_path))
        for line in diff:
            print(line)
        print("--- End of changes ---")

    return True


def main():
    parser = argparse.ArgumentParser(description="Update references from src/nova to src/nova/context_processor.")
    parser.add_argument("--apply", action="store_true", help="Apply changes to files, otherwise dry run.")
    args = parser.parse_args()

    # Root directory (your 'src' directory). Adjust as needed.
    root_dir = Path("src")

    updated_count = 0
    total_files = 0

    for path in root_dir.rglob("*"):
        if path.is_file():
            total_files += 1
            changed = update_paths_in_file(path, apply=args.apply)
            if changed:
                updated_count += 1

    if args.apply:
        print(f"\nUpdate complete. Changed {updated_count} file(s) out of {total_files}.")
    else:
        print(f"\nDry run complete. Would have changed {updated_count} file(s) out of {total_files}.")
        print("Re-run with --apply to actually update the files.")


if __name__ == "__main__":
    main() 