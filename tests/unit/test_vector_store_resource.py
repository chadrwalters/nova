"""Unit tests for vector store resource handler."""

from pathlib import Path
import pytest

from nova.server.resources.vector_store import VectorStoreHandler
from nova.server.types import ResourceError
from nova.vector_store.store import VectorStore


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    """Create temporary store path."""
    store_path = tmp_path / "vector_store"
    store_path.mkdir()
    return store_path


@pytest.fixture
def vector_store(store_path: Path) -> VectorStore:
    """Create vector store instance."""
    return VectorStore(store_path)


@pytest.fixture
def vector_store_handler(vector_store: VectorStore) -> VectorStoreHandler:
    """Create vector store handler."""
    return VectorStoreHandler(vector_store)


def test_initialization(vector_store_handler: VectorStoreHandler) -> None:
    """Test vector store initialization."""
    metadata = vector_store_handler.get_metadata()
    assert metadata["id"] == "vector-store"
    assert metadata["type"] == "VECTOR_STORE"
    assert metadata["name"] == "Vector Store"  # type: ignore[unreachable]
    assert (
        metadata["attributes"]["collection_name"] == VectorStoreHandler.COLLECTION_NAME
    )
    assert (
        metadata["attributes"]["embedding_dimension"]
        == VectorStoreHandler.EMBEDDING_DIMENSION
    )
    assert metadata["attributes"]["total_vectors"] == 0
    assert metadata["attributes"]["index_type"] == VectorStoreHandler.INDEX_TYPE


def test_add_vectors(vector_store_handler: VectorStoreHandler) -> None:
    """Test adding vectors."""
    ids = ["test1", "test2"]
    embeddings = [
        [0.1] * VectorStoreHandler.EMBEDDING_DIMENSION,
        [0.2] * VectorStoreHandler.EMBEDDING_DIMENSION,
    ]
    metadatas = [{"source": "test1"}, {"source": "test2"}]

    # Track changes
    changes: list[bool] = []
    vector_store_handler.on_change(lambda: changes.append(True))

    # Add vectors
    vector_store_handler.add_vectors(ids, embeddings, metadatas)

    # Verify changes
    assert len(changes) == 1

    # Query to verify vectors were added
    query_embedding = [[0.15] * VectorStoreHandler.EMBEDDING_DIMENSION]
    results = vector_store_handler.query_vectors(
        query_embedding, n_results=2, min_score=0.0
    )
    assert len(results) == 2


def test_query_vectors(vector_store_handler: VectorStoreHandler) -> None:
    """Test querying vectors."""
    # Add test vectors
    ids = ["test1", "test2"]
    embeddings = [
        [0.1] * VectorStoreHandler.EMBEDDING_DIMENSION,
        [0.2] * VectorStoreHandler.EMBEDDING_DIMENSION,
    ]
    metadatas = [{"source": "test1"}, {"source": "test2"}]
    vector_store_handler.add_vectors(ids, embeddings, metadatas)

    # Query vectors
    query_embedding = [[0.15] * VectorStoreHandler.EMBEDDING_DIMENSION]
    results = vector_store_handler.query_vectors(
        query_embedding, n_results=2, min_score=0.0
    )

    # Verify results
    assert len(results) == 2
    assert all(isinstance(r["score"], float) for r in results)
    assert all(0 <= r["score"] <= 1 for r in results)
    assert all(r["id"] in ids for r in results)
    assert all(isinstance(r["metadata"], dict) for r in results)


def test_delete_vectors(vector_store_handler: VectorStoreHandler) -> None:
    """Test deleting vectors."""
    # Add test vectors
    ids = ["test1", "test2"]
    embeddings = [
        [0.1] * VectorStoreHandler.EMBEDDING_DIMENSION,
        [0.2] * VectorStoreHandler.EMBEDDING_DIMENSION,
    ]
    metadatas = [{"source": "test1"}, {"source": "test2"}]
    vector_store_handler.add_vectors(ids, embeddings, metadatas)

    # Track changes
    changes: list[bool] = []
    vector_store_handler.on_change(lambda: changes.append(True))

    # Delete vectors
    vector_store_handler.delete_vectors(["test1"])

    # Verify changes
    assert len(changes) == 1

    # Query to verify deletion
    query_embedding = [[0.15] * VectorStoreHandler.EMBEDDING_DIMENSION]
    results = vector_store_handler.query_vectors(
        query_embedding, n_results=2, min_score=0.0
    )
    assert len(results) == 1
    assert results[0]["id"] == "test2"


def test_validate_access(vector_store_handler: VectorStoreHandler) -> None:
    """Test access validation."""
    assert vector_store_handler.validate_access("read")
    assert vector_store_handler.validate_access("write")
    assert vector_store_handler.validate_access("delete")
    assert not vector_store_handler.validate_access("invalid")


def test_add_vectors_validation(vector_store_handler: VectorStoreHandler) -> None:
    """Test add vectors input validation."""
    # Test empty inputs
    with pytest.raises(ResourceError, match="Empty ids or embeddings list"):
        vector_store_handler.add_vectors([], [])

    # Test mismatched lengths
    with pytest.raises(ResourceError, match="Mismatched number of ids and embeddings"):
        vector_store_handler.add_vectors(
            ["test1"],
            [
                [0.1] * VectorStoreHandler.EMBEDDING_DIMENSION,
                [0.2] * VectorStoreHandler.EMBEDDING_DIMENSION,
            ],
        )

    # Test wrong embedding dimension
    with pytest.raises(ResourceError, match="Invalid embedding dimension"):
        vector_store_handler.add_vectors(["test1"], [[0.1] * 10])

    # Test mismatched metadata
    with pytest.raises(ResourceError, match="Mismatched number of metadatas"):
        vector_store_handler.add_vectors(
            ["test1", "test2"],
            [
                [0.1] * VectorStoreHandler.EMBEDDING_DIMENSION,
                [0.2] * VectorStoreHandler.EMBEDDING_DIMENSION,
            ],
            [{"source": "test1"}],
        )


def test_query_vectors_validation(vector_store_handler: VectorStoreHandler) -> None:
    """Test query vectors input validation."""
    # Test empty query
    with pytest.raises(ResourceError, match="Empty query embeddings list"):
        vector_store_handler.query_vectors([])

    # Test wrong dimension
    with pytest.raises(ResourceError, match="Invalid query dimension"):
        vector_store_handler.query_vectors([[0.1] * 10])

    # Test invalid n_results
    with pytest.raises(ResourceError, match="n_results must be positive"):
        vector_store_handler.query_vectors(
            [[0.1] * VectorStoreHandler.EMBEDDING_DIMENSION], n_results=0
        )

    # Test invalid min_score
    with pytest.raises(ResourceError, match="min_score must be between 0 and 1"):
        vector_store_handler.query_vectors(
            [[0.1] * VectorStoreHandler.EMBEDDING_DIMENSION], min_score=2.0
        )


def test_delete_vectors_validation(vector_store_handler: VectorStoreHandler) -> None:
    """Test delete vectors input validation."""
    # Test empty ids
    with pytest.raises(ResourceError, match="Empty ids list"):
        vector_store_handler.delete_vectors([])


def test_on_change_validation(vector_store_handler: VectorStoreHandler) -> None:
    """Test on_change input validation."""
    # Test non-callable
    with pytest.raises(ValueError, match="Callback must be callable"):
        vector_store_handler.on_change("not_callable")  # type: ignore


def test_change_callback_error_handling(
    vector_store_handler: VectorStoreHandler,
) -> None:
    """Test error handling in change callbacks."""

    def failing_callback() -> None:
        raise Exception("Test error")

    def working_callback() -> None:
        pass

    # Register callbacks
    vector_store_handler.on_change(failing_callback)
    vector_store_handler.on_change(working_callback)

    # Add vectors to trigger callbacks
    ids = ["test1"]
    embeddings = [[0.1] * VectorStoreHandler.EMBEDDING_DIMENSION]
    vector_store_handler.add_vectors(ids, embeddings)  # Should not raise exception
