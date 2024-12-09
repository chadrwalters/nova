#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Running Nova Tests${NC}"

# Ensure we're using poetry
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}❌ Poetry is not installed. Please install it first.${NC}"
    exit 1
fi

# Create necessary directories
mkdir -p tests/fixtures

# Run the tests with proper formatting
echo -e "\n${BLUE}🧪 Running tests...${NC}\n"

poetry run pytest \
    -v \
    --color=yes \
    tests/ \
    "$@"

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed successfully!${NC}\n"
else
    echo -e "\n${RED}❌ Some tests failed${NC}\n"
    exit $TEST_EXIT_CODE
fi
