#!/bin/bash

# Default values
COVERAGE=0
VERBOSE=0
FAILFAST=0
SPECIFIC_TEST=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE=1
            shift
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        --failfast)
            FAILFAST=1
            shift
            ;;
        --test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Ensure we're using the correct virtual environment
VENV_PATH=".venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment not found. Running poetry install..."
    poetry install
fi

# Build the pytest command
PYTEST_CMD="poetry run pytest"

# Add options based on flags
if [ $VERBOSE -eq 1 ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ $FAILFAST -eq 1 ]; then
    PYTEST_CMD="$PYTEST_CMD --failfast"
fi

if [ $COVERAGE -eq 1 ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=term-missing --cov-report=html"
fi

if [ ! -z "$SPECIFIC_TEST" ]; then
    PYTEST_CMD="$PYTEST_CMD $SPECIFIC_TEST"
else
    PYTEST_CMD="$PYTEST_CMD tests/"
fi

# Create necessary directories
mkdir -p tests/fixtures

# Run the tests
echo "Running tests with command: $PYTEST_CMD"
$PYTEST_CMD

# If coverage was run, provide the report location
if [ $COVERAGE -eq 1 ]; then
    echo "Coverage report generated in htmlcov/index.html"
fi
