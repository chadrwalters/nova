#!/bin/bash

# Set up error handling
set -e

# Load environment variables
if [ -f .env ]; then
    source .env
fi

# Activate virtual environment
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found. Please run ./install.sh first"
    exit 1
fi

# Verify pytest is installed
if ! python -m pytest --version > /dev/null 2>&1; then
    echo "Error: pytest not found. Please run ./install.sh to install dependencies"
    exit 1
fi

# Default values
VERBOSE=false
COVERAGE=false
FAIL_FAST=false
TEST_FILE=""
PYTEST_ARGS=""

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            PYTEST_ARGS="$PYTEST_ARGS -v"
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -f|--fail-fast)
            FAIL_FAST=true
            PYTEST_ARGS="$PYTEST_ARGS -x"
            shift
            ;;
        -t|--test)
            TEST_FILE="$2"
            shift
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -v, --verbose     Show detailed test output"
            echo "  -c, --coverage    Generate coverage report"
            echo "  -f, --fail-fast   Stop on first failure"
            echo "  -t, --test FILE   Run specific test file"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create test directories
echo "===== Setting up Test Environment ====="
mkdir -p tests/data
mkdir -p tests/output
mkdir -p tests/temp

# Set up Python path
export PYTHONPATH="$PYTHONPATH:$(pwd)/src"

# Build coverage command
if [ "$COVERAGE" = true ]; then
    COVERAGE_CMD="--cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=80"
else
    COVERAGE_CMD=""
fi

# Run all tests
echo -e "\n===== Running Tests ====="
if [ -n "$TEST_FILE" ]; then
    python -m pytest $PYTEST_ARGS $COVERAGE_CMD "$TEST_FILE"
else
    python -m pytest $PYTEST_ARGS $COVERAGE_CMD tests/
fi

# Store test exit code
TEST_EXIT_CODE=$?

# Clean up test artifacts
echo -e "\n===== Cleaning Up Test Environment ====="
find tests/temp -mindepth 1 -delete 2>/dev/null || true

# Preserve test outputs if coverage was requested
if [ "$COVERAGE" = true ]; then
    echo "Coverage report saved to htmlcov/"
else
    rm -rf tests/output/* 2>/dev/null || true
fi

# Deactivate virtual environment
deactivate

# Exit with test status
exit $TEST_EXIT_CODE 