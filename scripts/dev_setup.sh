#!/usr/bin/env bash
set -eo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Selecta development environment...${NC}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}UV not found. Installing UV...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Ensure uv is in PATH
    export PATH="$HOME/.local/bin:$PATH"
    # Check if installation was successful
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}Failed to install uv. Please install manually and try again.${NC}"
        exit 1
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    uv venv
else
    echo -e "${BLUE}Virtual environment already exists.${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install project dependencies
echo -e "${BLUE}Installing project dependencies...${NC}"
uv pip install -e ".[dev]"

# Initialize pre-commit
echo -e "${BLUE}Setting up pre-commit hooks...${NC}"
pre-commit install

echo -e "${GREEN}Development environment setup complete!${NC}"
echo -e "${BLUE}To activate the environment, run:${NC} source .venv/bin/activate"
