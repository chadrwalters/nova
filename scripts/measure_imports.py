"""
Measure import times for Nova modules.
"""

import importlib
import statistics
import time
from typing import Dict, List, NoReturn, Union, cast

MODULES_TO_TEST = [
    "nova.context_processor.config.manager",
    "nova.context_processor.handlers.base",
    "nova.context_processor.handlers.registry",
    "nova.context_processor.handlers.image",
    "nova.context_processor.handlers.document",
    "nova.context_processor.handlers.markdown",
    "nova.context_processor.phases.parse",
    "nova.context_processor.phases.split",
    "nova.context_processor.phases.finalize",
    "nova.context_processor.phases.disassemble",
    "nova.context_processor.utils.markdown",
    "nova.context_processor.utils.path_utils",
    "nova.context_processor.utils.output_manager",
    "nova.context_processor.utils.file_utils",
]


def measure_import_time(module_name: str, iterations: int = 5) -> List[float]:
    """Measure import time for a module over multiple iterations."""
    times = []
    for _ in range(iterations):
        # Remove module if already imported
        if module_name in globals():
            del globals()[module_name]
        if module_name in locals():
            del locals()[module_name]

        # Clear module from sys.modules to force reload
        importlib.invalidate_caches()
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Measure import time
        start = time.perf_counter()
        importlib.import_module(module_name)
        end = time.perf_counter()
        times.append(end - start)

    return times


def main() -> NoReturn:
    """Run import time measurements."""
    results: Dict[str, Dict[str, Union[float, List[float]]]] = {}

    print("\nMeasuring import times...")
    print("-" * 60)
    print(f"{'Module':<40} {'Mean (ms)':<10} {'Std Dev':<10}")
    print("-" * 60)

    for module in MODULES_TO_TEST:
        times = measure_import_time(module)
        mean_time = statistics.mean(times) * 1000  # Convert to milliseconds
        std_dev = statistics.stdev(times) * 1000 if len(times) > 1 else 0

        results[module] = {"mean": mean_time, "std_dev": std_dev, "times": times}

        print(f"{module:<40} {mean_time:>8.2f}ms {std_dev:>8.2f}ms")

    print("-" * 60)
    total_mean = sum(cast(float, r["mean"]) for r in results.values())
    print(f"\nTotal mean import time: {total_mean:.2f}ms")

    sys.exit(0)


if __name__ == "__main__":
    import sys

    main()
