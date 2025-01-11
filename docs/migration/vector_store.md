# Vector Store Migration Guide

## Overview

The basic `VectorStore` implementation in `nova.processing` has been replaced with the advanced FAISS-based implementation from `nova.processing.vector_store`. This guide will help you migrate your code to use the new implementation.

## Changes

1. Import Path
   ```python
   # Old import
   from nova.processing import VectorStore, EphemeralVectorStore

   # New import
   from nova.processing.vector_store import VectorStore, EphemeralVectorStore
   ```

2. Additional Features
   The new implementation includes several improvements:
   - GPU acceleration support
   - Optimized batching for large datasets
   - Memory usage tracking
   - Performance metrics
   - IVF index support for faster search
   - Persistence support

## Migration Steps

1. Update your imports as shown above
2. If you're using GPU acceleration:
   ```python
   store = VectorStore(
       embedding_dim=384,
       use_gpu=True  # Will fallback to CPU if GPU is not available
   )
   ```

3. For large datasets, consider using IVF indexing:
   ```python
   store = VectorStore(
       embedding_dim=384,
       n_lists=100,  # Number of IVF lists
       n_probe=25    # Number of lists to probe during search
   )
   ```

4. If you need persistence:
   ```python
   # Save state
   store.save(Path("vector_store_state"))

   # Load state
   store = VectorStore()
   store.load(Path("vector_store_state"))
   ```

## Breaking Changes

1. The basic implementation's `_faiss_to_chunk_id` and `_chunk_id_to_faiss` mappings have been removed
2. The `EphemeralVectorStore` now requires string IDs for chunks
3. The cleanup mechanism in `EphemeralVectorStore` has been optimized and may behave differently

## Need Help?

If you encounter any issues during migration, please:
1. Check the test files in `tests/test_processing.py` for examples
2. Review the API documentation
3. Open an issue on GitHub 