def _show_stats(self) -> None:
    """Show system statistics."""
    print("\nVector Store Stats:")
    stats = self.vector_store.stats
    print(f"Total chunks: {stats.total_chunks}")
    print(f"Total embeddings: {stats.total_embeddings}")
    print(f"Total searches: {stats.total_searches}")
    print(f"Cache hits: {stats.cache_hits}")
    print(f"Cache misses: {stats.cache_misses}")
    print(f"Average chunk size: {stats.avg_chunk_size:.2f}")
    print(f"Last update: {stats.last_update}")

    print("\nLog Stats:")
    log_stats = self.log_manager.get_log_stats()
    print(f"Current log size: {log_stats['current_size']} bytes")
    print(f"Archive count: {log_stats['archive_count']}")
    print(f"Total archive size: {log_stats['total_archive_size']} bytes")
    print(f"Last rotation: {log_stats['last_rotation']}")
