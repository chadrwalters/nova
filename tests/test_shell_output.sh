#!/bin/bash

# Colors for test output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to test color output
test_color_output() {
    echo -e "\n${BLUE}Testing color output:${NC}"
    echo -e "${GREEN}✓ Success message${NC}"
    echo -e "${RED}✗ Error message${NC}"
    echo -e "${YELLOW}! Warning message${NC}"
    echo -e "${BLUE}i Information message${NC}"
}

# Function to test no-color output
test_no_color_output() {
    echo -e "\nTesting no-color output:"
    NO_COLOR=1 echo "✓ Success message"
    NO_COLOR=1 echo "✗ Error message"
    NO_COLOR=1 echo "! Warning message"
    NO_COLOR=1 echo "i Information message"
}

echo -e "${BLUE}Starting shell output tests...${NC}"

# Run tests
test_color_output
test_no_color_output

echo -e "\n${GREEN}All shell output tests completed${NC}"