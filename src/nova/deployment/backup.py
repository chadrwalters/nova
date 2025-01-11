#!/usr/bin/env python3
"""Backup and restore functionality for Nova."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


def create_backup(backup_dir: Optional[Path] = None, data_dir: Optional[Path] = None) -> Path:
    """Create a backup of Nova data."""
    if backup_dir is None:
        backup_dir = Path("data/backup")
        
    if data_dir is None:
        data_dir = Path("data")
        
    # Create timestamp for backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"nova_backup_{timestamp}"
    
    try:
        # Create backup directory
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Backup data directory
        if data_dir.exists():
            shutil.copytree(
                data_dir,
                backup_path / "data",
                dirs_exist_ok=True
            )
            
        # Create backup metadata
        metadata = {
            "timestamp": timestamp,
            "data_dir": str(data_dir)
        }
        
        with open(backup_path / "metadata.json", "w") as f:
            yaml.dump(metadata, f, default_flow_style=False)
            
        print(f"Backup created successfully at {backup_path}")
        return backup_path
    except Exception as e:
        raise RuntimeError(f"Backup failed: {e}")


def restore_backup(backup_dir: Path, data_dir: Optional[Path] = None) -> None:
    """Restore Nova data from backup."""
    try:
        # Validate backup
        if not backup_dir.exists():
            raise ValueError(f"Backup directory not found: {backup_dir}")
            
        # Load backup metadata
        metadata_path = backup_dir / "metadata.json"
        if not metadata_path.exists():
            raise ValueError("Backup metadata not found")
            
        with open(metadata_path) as f:
            metadata = yaml.safe_load(f)
            
        # Use provided data directory or one from metadata
        if data_dir is None:
            data_dir = Path(metadata["data_dir"])
            
        # Restore data directory
        data_backup = backup_dir / "data"
        if data_backup.exists():
            # Create parent directories
            data_dir.parent.mkdir(parents=True, exist_ok=True)
            
            # Remove existing data
            if data_dir.exists():
                shutil.rmtree(data_dir)
                
            # Restore from backup
            shutil.copytree(data_backup, data_dir)
        else:
            raise ValueError("Data backup not found")
            
        print("Restore completed successfully")
    except Exception as e:
        raise RuntimeError(f"Restore failed: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Nova backup and restore utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a backup")
    backup_parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Backup directory path"
    )
    backup_parser.add_argument(
        "--data-dir",
        type=Path,
        help="Data directory to backup"
    )
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument(
        "backup_dir",
        type=Path,
        help="Backup directory path"
    )
    restore_parser.add_argument(
        "--data-dir",
        type=Path,
        help="Data directory to restore to"
    )
    
    args = parser.parse_args()
    
    if args.command == "backup":
        create_backup(args.backup_dir, args.data_dir)
    elif args.command == "restore":
        restore_backup(args.backup_dir, args.data_dir)
    else:
        parser.print_help() 