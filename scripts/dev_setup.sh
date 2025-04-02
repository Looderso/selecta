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
    # Use Python's built-in venv module instead of uv venv
    python3 -m venv .venv
else
    echo -e "${YELLOW}Virtual environment already exists. Checking for pip...${NC}"
    # Check if pip exists in the venv
    if [ ! -f ".venv/bin/pip" ] && [ ! -f ".venv/bin/pip3" ]; then
        echo -e "${RED}Existing venv is missing pip. Recreating...${NC}"
        rm -rf .venv
        python3 -m venv .venv
    fi
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source .venv/bin/activate

# Verify pip is available
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Pip not found in virtual environment. Installing...${NC}"
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python get-pip.py
    rm get-pip.py
fi

# Update pip in the virtual environment
echo -e "${BLUE}Updating pip in virtual environment...${NC}"
python -m pip install --upgrade pip

# Install project dependencies with uv
echo -e "${BLUE}Installing project dependencies with uv...${NC}"
uv pip install -e ".[dev]"

# Initialize pre-commit
echo -e "${BLUE}Setting up pre-commit hooks...${NC}"
pre-commit install

# Verify environment is working
VENV_PYTHON=$(which python)
VENV_PIP=$(which pip || which pip3)

echo -e "${GREEN}Environment verification:${NC}"
echo -e "Python: ${VENV_PYTHON}"
echo -e "Pip: ${VENV_PIP}"

echo -e "${GREEN}Development environment setup complete!${NC}"
echo -e "${BLUE}To activate the environment, run:${NC} source .venv/bin/activate"
