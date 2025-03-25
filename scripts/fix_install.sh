#!/usr/bin/env bash
set -eo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Fixing Selecta installation...${NC}"

# Ensure we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}No active virtual environment detected.${NC}"
    if [ -d ".venv" ]; then
        echo -e "${BLUE}Activating virtual environment...${NC}"
        source .venv/bin/activate
    else
        echo -e "${RED}No .venv directory found. Please activate your virtual environment first.${NC}"
        exit 1
    fi
fi

# Reinstall the package
echo -e "${BLUE}Reinstalling Selecta package...${NC}"
pip uninstall -y selecta
pip install -e .

echo -e "${GREEN}Selecta package reinstalled.${NC}"
echo -e "${BLUE}Try running:${NC} selecta install-completion"
