#!/bin/bash

# Source environment variables
if [ -f .env ]; then
    source .env
else
    echo "Error: .env file not found"
    exit 1
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed"
    exit 1
fi

# Check pytest installation
if ! python3 -c "import pytest" &> /dev/null; then
    echo "Error: pytest is required but not installed"
    echo "Installing pytest..."
    python3 -m pip install pytest
fi

# Parse command line arguments
VERBOSE=0
COVERAGE=0
SPECIFIC_TEST=""
FAIL_FAST=0

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -c|--coverage)
            COVERAGE=1
            shift
            ;;
        -f|--fail-fast)
            FAIL_FAST=1
            shift
            ;;
        -t|--test)
            SPECIFIC_TEST="$2"
            shift
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -v, --verbose     Show verbose test output"
            echo "  -c, --coverage    Run tests with coverage report"
            echo "  -f, --fail-fast   Stop on first test failure"
            echo "  -t, --test FILE   Run specific test file"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set up test environment
echo "Setting up test environment..."

# Create test directories if they don't exist
for dir in "data" "output" "temp"; do
    mkdir -p "tests/$dir"
done

# Build pytest command
PYTEST_CMD="python3 -m pytest"

# Add options based on arguments
if [ $VERBOSE -eq 1 ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ $COVERAGE -eq 1 ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src/nova --cov-report=term-missing"
fi

if [ $FAIL_FAST -eq 1 ]; then
    PYTEST_CMD="$PYTEST_CMD -x"
fi

# Add specific test if provided, otherwise run all tests
if [ -n "$SPECIFIC_TEST" ]; then
    if [ -f "tests/$SPECIFIC_TEST" ]; then
        PYTEST_CMD="$PYTEST_CMD tests/$SPECIFIC_TEST"
    else
        echo "Error: Test file '$SPECIFIC_TEST' not found"
        exit 1
    fi
else
    PYTEST_CMD="$PYTEST_CMD tests/"
fi

# Set PYTHONPATH to include src directory
export PYTHONPATH="$PYTHONPATH:$(pwd)/src"

# Run the tests
echo "Running tests..."
echo "Command: $PYTEST_CMD"
$PYTEST_CMD

# Store exit code
TEST_EXIT_CODE=$?

# Clean up temporary test files
echo "Cleaning up test environment..."
rm -rf tests/temp/*

# Exit with test result
exit $TEST_EXIT_CODE 