"""Performance test configuration and fixtures."""

import functools
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar, cast
from collections.abc import Callable

import pytest

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


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


def benchmark(
    iterations: int = 100,
    warmup: int = 10,
    setup: Callable[[], Any] | None = None,
    cleanup: Callable[[], None] | None = None,
) -> Callable[[F], F]:
    """Decorator for benchmarking functions.

    Args:
        iterations: Number of iterations to run
        warmup: Number of warmup iterations
        setup: Setup function to run before each iteration
        cleanup: Cleanup function to run after each iteration

    Returns:
        Decorated function that returns benchmark results
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> None:
            # Run warmup iterations
            for _ in range(warmup):
                if setup:
                    setup()
                func(*args, **kwargs)
                if cleanup:
                    cleanup()

            # Run benchmark iterations
            samples: list[float] = []
            for _ in range(iterations):
                if setup:
                    setup()

                start = time.perf_counter()
                func(*args, **kwargs)
                end = time.perf_counter()

                if cleanup:
                    cleanup()

                samples.append(end - start)

            # Calculate statistics
            total_time = sum(samples)
            avg_time = total_time / iterations
            min_time = min(samples)
            max_time = max(samples)

            result = BenchmarkResult(
                name=func.__name__,
                operation=func.__doc__ or "unknown",
                iterations=iterations,
                total_time=total_time,
                avg_time=avg_time,
                min_time=min_time,
                max_time=max_time,
                samples=samples,
            )

            # Print benchmark results
            print(f"\n{result}")

            # Assert performance constraints
            assert (
                avg_time < 1.0
            ), f"Average time {avg_time:.3f}s exceeds 1.0s threshold"
            assert (
                max_time < 2.0
            ), f"Maximum time {max_time:.3f}s exceeds 2.0s threshold"

        return cast(F, wrapper)

    return decorator


@pytest.fixture
def benchmark_dir(temp_dir: Path) -> Path:
    """Create benchmark data directory.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to benchmark data directory
    """
    bench_dir = temp_dir / "benchmark_data"
    bench_dir.mkdir(parents=True)
    return bench_dir


@pytest.fixture
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
