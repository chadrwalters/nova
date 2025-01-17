"""Performance test configuration and fixtures."""

import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TypeVar, cast, runtime_checkable

import pytest

T = TypeVar("T")
SyncF = TypeVar("SyncF", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Awaitable[Any]])


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    name: str
    operation: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    samples: list[float]

    def __str__(self) -> str:
        """Format benchmark results as string."""
        return (
            f"{self.name} - {self.operation}:\n"
            f"  Iterations: {self.iterations}\n"
            f"  Total time: {self.total_time:.3f}s\n"
            f"  Average time: {self.avg_time:.3f}s\n"
            f"  Min time: {self.min_time:.3f}s\n"
            f"  Max time: {self.max_time:.3f}s"
        )


@runtime_checkable
class BenchmarkableFunction(Protocol):
    """Protocol for functions that can be benchmarked."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


def benchmark(
    iterations: int = 100, warmup: int = 10
) -> Callable[[BenchmarkableFunction], BenchmarkableFunction]:
    """Benchmark decorator for measuring function performance.

    Args:
        iterations: Number of iterations to run
        warmup: Number of warmup iterations

    Returns:
        Decorated function
    """

    def decorator(func: BenchmarkableFunction) -> BenchmarkableFunction:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Run warmup iterations
            for _ in range(warmup):
                func(*args, **kwargs)

            # Run benchmark iterations
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                func(*args, **kwargs)
                end = time.perf_counter()
                times.append(end - start)

            # Calculate statistics
            total_time = sum(times)
            avg_time = total_time / iterations
            min_time = min(times)
            max_time = max(times)

            print(f"\nBenchmark results for {getattr(func, '__name__', 'unknown')}:")
            print(f"  Total time: {total_time:.4f}s")
            print(f"  Average time: {avg_time:.4f}s")
            print(f"  Min time: {min_time:.4f}s")
            print(f"  Max time: {max_time:.4f}s")

            return func(*args, **kwargs)

        # Preserve pytest marks
        if hasattr(func, "pytestmark"):
            wrapper.pytestmark = func.pytestmark  # type: ignore

        # Preserve pytest parametrize
        if hasattr(func, "parametrize"):
            wrapper.parametrize = func.parametrize  # type: ignore

        return cast(BenchmarkableFunction, wrapper)

    return decorator


@pytest.fixture(scope="module")
def benchmark_dir(temp_dir: Path) -> Path:
    """Create benchmark data directory.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to benchmark data directory
    """
    bench_dir = temp_dir / "benchmark_data"
    bench_dir.mkdir(parents=True)
    # Ensure directory has write permissions
    os.chmod(bench_dir, 0o755)
    return bench_dir


@pytest.fixture(scope="module")
def sample_documents(benchmark_dir: Path) -> list[dict[str, Any]]:
    """Create sample documents for benchmarking.

    Args:
        benchmark_dir: Benchmark data directory

    Returns:
        List of sample documents
    """
    docs = []
    for i in range(1000):
        doc = {
            "id": f"doc_{i}",
            "title": f"Document {i}",
            "content": f"This is the content of document {i}. " * 10,
            "metadata": {
                "author": f"Author {i % 10}",
                "tags": [f"tag_{j}" for j in range(i % 5)],
                "created": time.time(),
            },
        }
        docs.append(doc)
    return docs


@pytest.fixture(autouse=True)
def benchmark_fixture(request: pytest.FixtureRequest) -> None:
    """Benchmark fixture for measuring function performance."""
    if request.node.get_closest_marker("benchmark"):
        iterations = 100
        warmup = 10
        func = request.function

        # Run warmup iterations
        for _ in range(warmup):
            func(request)

        # Run benchmark iterations
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func(request)
            end = time.perf_counter()
            times.append(end - start)

        # Calculate statistics
        total_time = sum(times)
        avg_time = total_time / iterations
        min_time = min(times)
        max_time = max(times)

        print(f"\nBenchmark results for {func.__name__}:")
        print(f"  Total time: {total_time:.4f}s")
        print(f"  Average time: {avg_time:.4f}s")
        print(f"  Min time: {min_time:.4f}s")
        print(f"  Max time: {max_time:.4f}s")
