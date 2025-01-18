"""Performance profiling for Nova system.

This module provides profiling capabilities for CPU, memory, and I/O operations.
"""

import cProfile
import io
import json
import logging
import pstats
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, cast

import psutil
from psutil import Process

logger = logging.getLogger(__name__)


@dataclass
class ProfileStats:
    """Profile statistics."""

    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    io_read_mb: float = 0.0
    io_write_mb: float = 0.0
    profile_stats: Optional[pstats.Stats] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary.

        Returns:
            Dict containing profile statistics
        """
        return {
            "timing": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration": self.duration,
            },
            "resources": {
                "cpu_percent": self.cpu_percent,
                "memory_mb": self.memory_mb,
                "io": {
                    "read_mb": self.io_read_mb,
                    "write_mb": self.io_write_mb,
                },
            },
        }


class Profiler:
    """Performance profiler."""

    def __init__(self, base_path: Path):
        """Initialize profiler.

        Args:
            base_path: Base path for storing profile data
        """
        self.base_path = base_path
        self.profiles_dir = base_path / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.process = cast(Process, psutil.Process())
        self._current_profile: Optional[ProfileStats] = None
        self._profiler: Optional[cProfile.Profile] = None

    @contextmanager
    def profile(self, name: str) -> Generator[ProfileStats, None, None]:
        """Profile a code block.

        Args:
            name: Profile name

        Yields:
            Profile statistics
        """
        # Initialize profiler
        self._profiler = cProfile.Profile()
        self._profiler.enable()

        # Initialize stats
        self._current_profile = ProfileStats(start_time=datetime.now())

        # Get initial I/O counters
        io_start = self.process.io_counters()  # type: ignore

        try:
            yield self._current_profile

        finally:
            # Stop profiler
            self._profiler.disable()

            # Get final measurements
            end_time = datetime.now()
            io_end = self.process.io_counters()  # type: ignore

            if self._current_profile:
                # Update stats
                self._current_profile.end_time = end_time
                self._current_profile.duration = (end_time - self._current_profile.start_time).total_seconds()
                self._current_profile.cpu_percent = self.process.cpu_percent()
                self._current_profile.memory_mb = self.process.memory_info().rss / 1024 / 1024
                self._current_profile.io_read_mb = (io_end.read_bytes - io_start.read_bytes) / 1024 / 1024
                self._current_profile.io_write_mb = (io_end.write_bytes - io_start.write_bytes) / 1024 / 1024

                # Save profile data
                self._save_profile(name, self._current_profile)

            # Clear current profile
            self._current_profile = None
            self._profiler = None

    def _save_profile(self, name: str, stats: ProfileStats) -> None:
        """Save profile data.

        Args:
            name: Profile name
            stats: Profile statistics
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_path = self.profiles_dir / f"{name}_{timestamp}"

        try:
            # Save stats as JSON
            stats_path = profile_path.with_suffix(".json")
            stats_path.write_text(json.dumps(stats.to_dict(), indent=2))

            # Save cProfile data if available
            if self._profiler:
                profile_stats = pstats.Stats(self._profiler)
                stats_file = io.StringIO()
                profile_stats.stream = stats_file  # type: ignore
                profile_stats.sort_stats("cumulative")
                profile_stats.print_stats()

                profile_text = stats_file.getvalue()
                profile_path.with_suffix(".prof").write_text(profile_text)

        except Exception as e:
            logger.error(f"Error saving profile data: {e}")

    def get_profiles(self) -> List[Dict[str, Any]]:
        """Get list of available profiles.

        Returns:
            List of profile information
        """
        profiles = []
        for stats_file in sorted(self.profiles_dir.glob("*.json")):
            try:
                stats = json.loads(stats_file.read_text())
                name = stats_file.stem.rsplit("_", 1)[0]
                profiles.append({
                    "name": name,
                    "timestamp": stats["timing"]["start_time"],
                    "duration": stats["timing"]["duration"],
                    "stats_file": str(stats_file),
                    "profile_file": str(stats_file.with_suffix(".prof")),
                })
            except Exception as e:
                logger.error(f"Error reading profile {stats_file}: {e}")

        return profiles

    def cleanup_old_profiles(self, max_age_days: int = 7) -> None:
        """Clean up old profile data.

        Args:
            max_age_days: Maximum age of profiles in days
        """
        cutoff = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)

        for profile_file in self.profiles_dir.glob("*.*"):
            try:
                if profile_file.stat().st_mtime < cutoff:
                    profile_file.unlink()
            except Exception as e:
                logger.error(f"Error cleaning up profile {profile_file}: {e}")
