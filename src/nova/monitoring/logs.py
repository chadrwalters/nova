"""Log management utilities."""
import gzip
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path


class LogManager:
    """Manager for log files and analysis."""

    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_LOG_AGE = timedelta(days=7)  # 7 days
    MAX_ARCHIVE_FILES = 50

    def __init__(self, log_dir: str = ".nova/logs"):
        """Initialize log manager.

        Args:
            log_dir: Directory containing log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir = self.log_dir / "archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def rotate_logs(self) -> None:
        """Rotate log files based on size and age."""
        if not self.log_dir.exists():
            return

        # Check each log file
        for log_file in self.log_dir.glob("*.log"):
            try:
                # Check file size
                if log_file.stat().st_size > self.MAX_LOG_SIZE:
                    self._archive_log(log_file)
                    continue

                # Check file age
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if datetime.now() - mtime > self.MAX_LOG_AGE:
                    self._archive_log(log_file)

            except Exception as e:
                logging.error(f"Error rotating log file {log_file}: {e}")

        # Clean up old archives
        self._cleanup_archives()

    def _archive_log(self, log_file: Path) -> None:
        """Archive a log file.

        Args:
            log_file: Path to log file
        """
        try:
            # Create archive filename with timestamp
            timestamp = datetime.fromtimestamp(log_file.stat().st_mtime)
            archive_name = f"{log_file.stem}_{timestamp.strftime('%Y%m%d_%H%M%S')}.log.gz"
            archive_path = self.archive_dir / archive_name

            # Compress and move to archive
            with open(log_file, "rb") as f_in:
                with gzip.open(archive_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove original file
            log_file.unlink()

        except Exception as e:
            logging.error(f"Error archiving log file {log_file}: {e}")

    def _cleanup_archives(self) -> None:
        """Clean up old archive files."""
        try:
            # Get all archive files sorted by modification time
            archives = sorted(self.archive_dir.glob("*.log.gz"), key=lambda x: x.stat().st_mtime)

            # Remove oldest files if we have too many
            while len(archives) > self.MAX_ARCHIVE_FILES:
                oldest = archives.pop(0)
                try:
                    oldest.unlink()
                except Exception as e:
                    logging.error(f"Error removing archive {oldest}: {e}")

        except Exception as e:
            logging.error(f"Error cleaning up archives: {e}")

    def get_stats(self) -> dict[str, int]:
        """Get statistics about log files.

        Returns:
            Dictionary with log statistics
        """
        stats = {
            "total_files": 0,
            "total_entries": 0,
            "error_entries": 0,
            "warning_entries": 0,
            "info_entries": 0,
        }

        if not self.log_dir.exists():
            return stats

        # Count log files
        log_files = list(self.log_dir.glob("*.log"))
        stats["total_files"] = len(log_files)

        # Parse log entries
        for log_file in log_files:
            try:
                with open(log_file) as f:
                    for line in f:
                        stats["total_entries"] += 1
                        if "ERROR" in line:
                            stats["error_entries"] += 1
                        elif "WARNING" in line:
                            stats["warning_entries"] += 1
                        elif "INFO" in line:
                            stats["info_entries"] += 1
            except Exception as e:
                logging.error(f"Error reading log file {log_file}: {e}")

        return stats

    def tail_logs(self, n: int = 10) -> list[dict[str, str]]:
        """Get the last n log entries.

        Args:
            n: Number of entries to return

        Returns:
            List of log entries with timestamp, level, component, and message
        """
        entries = []
        if not self.log_dir.exists():
            return entries

        # Get most recent log file
        log_files = sorted(
            self.log_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True
        )

        if not log_files:
            return entries

        # Read last n lines
        try:
            with open(log_files[0]) as f:
                lines = f.readlines()
                for line in lines[-n:]:
                    try:
                        # Parse log line
                        # Format: YYYY-MM-DD HH:MM:SS LEVEL component Message
                        parts = line.strip().split(" ", 3)
                        if len(parts) >= 4:
                            timestamp = f"{parts[0]} {parts[1]}"  # Combine date and time
                            entries.append(
                                {
                                    "timestamp": timestamp,
                                    "level": parts[2],
                                    "component": parts[3].split(" ", 1)[0],
                                    "message": parts[3].split(" ", 1)[1].strip(),
                                }
                            )
                    except Exception as e:
                        logging.error(f"Error parsing log line: {e}")
        except Exception as e:
            logging.error(f"Error reading log file: {e}")

        return list(reversed(entries))  # Return in reverse chronological order
