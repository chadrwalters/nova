"""Test script for validating logging features."""

import time
from pathlib import Path
from nova.core.logging import (
    setup_logger,
    create_progress,
    info,
    warning,
    error,
    success,
    path,
    detail,
    get_logger
)

def test_color_output():
    """Test all color output variations."""
    print("\nTesting color output:")
    info("This is an info message (cyan)")
    warning("This is a warning message (yellow)")
    error("This is an error message (red)")
    success("This is a success message (green)")
    path("This is a path message (magenta)")
    detail("This is a detail message (dim white)")

def test_progress_bars():
    """Test progress bars with different configurations."""
    print("\nTesting progress bars:")
    
    # Single progress bar
    with create_progress() as progress:
        task1 = progress.add_task("Processing files...", total=10)
        for i in range(10):
            time.sleep(0.1)
            progress.advance(task1)
    
    # Multiple concurrent progress bars
    with create_progress() as progress:
        task1 = progress.add_task("Task 1", total=5)
        task2 = progress.add_task("Task 2", total=3)
        task3 = progress.add_task("Task 3", total=2)
        
        for i in range(5):
            time.sleep(0.2)
            progress.advance(task1)
            if i < 3:
                progress.advance(task2)
            if i < 2:
                progress.advance(task3)

def test_log_levels():
    """Test different log levels."""
    logger = get_logger("test")
    print("\nTesting log levels:")
    
    logger.debug("Debug message - should only show in debug mode")
    logger.info("Info message - default visibility")
    logger.warning("Warning message - higher priority")
    logger.error("Error message - highest priority")

def main():
    """Run all logging tests."""
    info("Starting logging validation tests")
    
    test_color_output()
    test_progress_bars()
    test_log_levels()
    
    success("All logging tests completed successfully")

if __name__ == "__main__":
    main() 