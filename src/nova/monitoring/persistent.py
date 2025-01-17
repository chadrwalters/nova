"""Persistent monitoring for Nova system.

This module handles cross-session metrics, logging, and system health
tracking. Data is stored in the .nova directory to persist between
Claude Desktop sessions.
"""

import logging
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PersistentMonitor:
    """Manages persistent monitoring data across sessions."""

    def __init__(self, base_path: Path):
        """Initialize persistent monitor.

        Args:
            base_path: Base path for Nova system
        """
        self.base_path = base_path
        self.metrics_path = base_path / "metrics"
        self.metrics_path.mkdir(exist_ok=True)

        # Initialize SQLite database for metrics
        self.db_path = self.metrics_path / "metrics.db"
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database for metrics storage."""
        with self._get_db() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    queries_processed INTEGER,
                    avg_query_time REAL,
                    peak_memory_mb REAL,
                    errors_encountered INTEGER
                );

                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    timestamp TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    timestamp TIMESTAMP,
                    cpu_percent REAL,
                    memory_mb REAL,
                    disk_usage_percent REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
            """
            )

    @contextmanager
    def _get_db(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record_session_end(self, session_metrics: dict[str, Any]) -> None:
        """Record metrics from a completed session.

        Args:
            session_metrics: Metrics from the session
        """
        with self._get_db() as conn:
            # Insert session record
            cursor = conn.execute(
                """
                INSERT INTO sessions (
                    start_time, end_time, queries_processed,
                    avg_query_time, peak_memory_mb, errors_encountered
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    session_metrics["session"]["start_time"],
                    datetime.now().isoformat(),
                    session_metrics["session"]["queries_processed"],
                    session_metrics["session"]["avg_query_time"],
                    session_metrics["session"]["peak_memory_mb"],
                    session_metrics["session"]["errors"]["count"],
                ),
            )

            session_id = cursor.lastrowid

            # Record final error if exists
            if session_metrics["session"]["errors"]["last_error_time"]:
                conn.execute(
                    """
                    INSERT INTO errors (session_id, timestamp, error_message)
                    VALUES (?, ?, ?)
                """,
                    (
                        session_id,
                        session_metrics["session"]["errors"]["last_error_time"],
                        session_metrics["session"]["errors"]["last_error_message"],
                    ),
                )

            # Record final performance metrics
            conn.execute(
                """
                INSERT INTO performance_metrics (
                    session_id, timestamp, cpu_percent,
                    memory_mb, disk_usage_percent
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    datetime.now().isoformat(),
                    session_metrics["resources"]["cpu_percent"],
                    session_metrics["session"]["current_memory_mb"],
                    session_metrics["resources"]["disk_usage_percent"],
                ),
            )

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health status.

        Returns:
            Dict containing system health information
        """
        vector_store_path = self.base_path / "vectors"
        processing_path = self.base_path / "processing"
        logs_path = self.base_path / "logs"

        # Get disk space info
        disk_usage = shutil.disk_usage(str(self.base_path))

        with self._get_db() as conn:
            # Get recent errors
            recent_errors = conn.execute(
                """
                SELECT timestamp, error_message FROM errors
                WHERE timestamp > datetime('now', '-24 hours')
                ORDER BY timestamp DESC
            """
            ).fetchall()

            # Get session stats
            session_stats = conn.execute(
                """
                SELECT
                    COUNT(*) as total_sessions,
                    AVG(queries_processed) as avg_queries,
                    AVG(avg_query_time) as avg_query_time,
                    AVG(peak_memory_mb) as avg_peak_memory,
                    SUM(errors_encountered) as total_errors
                FROM sessions
                WHERE start_time > datetime('now', '-24 hours')
            """
            ).fetchone()

        return {
            "components": {
                "vector_store": {
                    "status": "healthy" if vector_store_path.exists() else "missing",
                    "size_mb": sum(f.stat().st_size for f in vector_store_path.rglob("*"))
                    / 1024
                    / 1024
                    if vector_store_path.exists()
                    else 0,
                },
                "processing": {
                    "status": "healthy" if processing_path.exists() else "missing",
                    "size_mb": sum(f.stat().st_size for f in processing_path.rglob("*"))
                    / 1024
                    / 1024
                    if processing_path.exists()
                    else 0,
                },
                "logs": {
                    "status": "healthy" if logs_path.exists() else "missing",
                    "size_mb": sum(f.stat().st_size for f in logs_path.rglob("*")) / 1024 / 1024
                    if logs_path.exists()
                    else 0,
                },
            },
            "storage": {
                "total_gb": disk_usage.total / (1024**3),
                "used_gb": disk_usage.used / (1024**3),
                "free_gb": disk_usage.free / (1024**3),
                "percent_used": (disk_usage.used / disk_usage.total) * 100,
            },
            "recent_activity": {
                "total_sessions": session_stats["total_sessions"],
                "avg_queries_per_session": session_stats["avg_queries"],
                "avg_query_time": session_stats["avg_query_time"],
                "avg_peak_memory_mb": session_stats["avg_peak_memory"],
                "total_errors": session_stats["total_errors"],
                "recent_errors": [
                    {"timestamp": row["timestamp"], "message": row["error_message"]}
                    for row in recent_errors
                ],
            },
        }

    def get_performance_trends(self, days: int = 7) -> dict[str, Any]:
        """Get performance trends over time.

        Args:
            days: Number of days to analyze

        Returns:
            Dict containing performance trends
        """
        with self._get_db() as conn:
            # Get daily stats
            daily_stats = conn.execute(
                """
                SELECT
                    date(start_time) as date,
                    COUNT(*) as sessions,
                    AVG(queries_processed) as avg_queries,
                    AVG(avg_query_time) as avg_query_time,
                    AVG(peak_memory_mb) as avg_peak_memory,
                    SUM(errors_encountered) as errors
                FROM sessions
                WHERE start_time > datetime('now', ? || ' days')
                GROUP BY date(start_time)
                ORDER BY date(start_time)
            """,
                (-days,),
            ).fetchall()

            # Get hourly performance metrics
            hourly_metrics = conn.execute(
                """
                SELECT
                    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                    AVG(cpu_percent) as avg_cpu,
                    AVG(memory_mb) as avg_memory,
                    AVG(disk_usage_percent) as avg_disk
                FROM performance_metrics
                WHERE timestamp > datetime('now', ? || ' days')
                GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
                ORDER BY hour
            """,
                (-days,),
            ).fetchall()

        return {
            "daily_stats": [
                {
                    "date": row["date"],
                    "sessions": row["sessions"],
                    "avg_queries": row["avg_queries"],
                    "avg_query_time": row["avg_query_time"],
                    "avg_peak_memory": row["avg_peak_memory"],
                    "errors": row["errors"],
                }
                for row in daily_stats
            ],
            "hourly_performance": [
                {
                    "hour": row["hour"],
                    "avg_cpu_percent": row["avg_cpu"],
                    "avg_memory_mb": row["avg_memory"],
                    "avg_disk_percent": row["avg_disk"],
                }
                for row in hourly_metrics
            ],
        }

    def get_error_summary(self, days: int = 7) -> dict[str, Any]:
        """Get summary of errors over time.

        Args:
            days: Number of days to analyze

        Returns:
            Dict containing error summary
        """
        with self._get_db() as conn:
            # Get error trends
            daily_errors = conn.execute(
                """
                SELECT
                    date(timestamp) as date,
                    COUNT(*) as error_count
                FROM errors
                WHERE timestamp > datetime('now', ? || ' days')
                GROUP BY date(timestamp)
                ORDER BY date(timestamp)
            """,
                (-days,),
            ).fetchall()

            # Get most common errors
            common_errors = conn.execute(
                """
                SELECT
                    error_message,
                    COUNT(*) as occurrence_count
                FROM errors
                WHERE timestamp > datetime('now', ? || ' days')
                GROUP BY error_message
                ORDER BY occurrence_count DESC
                LIMIT 5
            """,
                (-days,),
            ).fetchall()

        return {
            "error_trends": [
                {"date": row["date"], "count": row["error_count"]} for row in daily_errors
            ],
            "common_errors": [
                {"message": row["error_message"], "count": row["occurrence_count"]}
                for row in common_errors
            ],
        }
