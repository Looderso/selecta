#!/usr/bin/env bash
set -eo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if a shell was provided
if [ $# -lt 1 ]; then
    echo -e "${RED}Please specify a shell (bash, zsh, or fish)${NC}"
    echo -e "Usage: $0 <shell>"
    exit 1
fi

SHELL_TYPE=$1

# Validate shell type
if [[ ! "$SHELL_TYPE" =~ ^(bash|zsh|fish)$ ]]; then
    echo -e "${RED}Invalid shell type. Please use bash, zsh, or fish.${NC}"
    exit 1
fi

echo -e "${BLUE}Generating shell completion script for ${SHELL_TYPE}...${NC}"

# Determine the completion file path
case $SHELL_TYPE in
    bash)
        COMPLETION_FILE="$HOME/.selecta-complete.bash"
        RC_FILE="$HOME/.bashrc"
        SOURCE_CMD=". $COMPLETION_FILE"
        ;;
    zsh)
        COMPLETION_FILE="$HOME/.selecta-complete.zsh"
        RC_FILE="$HOME/.zshrc"
        SOURCE_CMD=". $COMPLETION_FILE"
        ;;
    fish)
        COMPLETION_FILE="$HOME/.config/fish/selecta-complete.fish"
        RC_FILE="$HOME/.config/fish/config.fish"
        SOURCE_CMD="source $COMPLETION_FILE"

        # Create directory if it doesn't exist
        mkdir -p "$(dirname "$COMPLETION_FILE")"
        ;;
esac

# Generate the completion script
echo -e "${BLUE}Saving completion script to $COMPLETION_FILE...${NC}"
env "_SELECTA_COMPLETE=${SHELL_TYPE}_source" selecta > "$COMPLETION_FILE"

# Check if script was generated successfully
if [ ! -s "$COMPLETION_FILE" ]; then
    echo -e "${RED}Failed to generate completion script.${NC}"
    exit 1
fi

echo -e "${GREEN}Completion script generated successfully at $COMPLETION_FILE${NC}"

# Check if the completion script is already sourced in the shell config
if grep -q "$SOURCE_CMD" "$RC_FILE" 2>/dev/null; then
    echo -e "${YELLOW}Completion script is already sourced in $RC_FILE${NC}"
else
    # Ask user if they want to add the source command to their shell config
    echo -e "${YELLOW}Would you like to add the following line to $RC_FILE?${NC}"
    echo -e "${BLUE}$SOURCE_CMD${NC}"

    read -p "Add to shell config? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "\n# Selecta shell completion\n$SOURCE_CMD" >> "$RC_FILE"
        echo -e "${GREEN}Added to $RC_FILE${NC}"
    else
        echo -e "${YELLOW}To manually enable completion, add this line to $RC_FILE:${NC}"
        echo -e "${BLUE}$SOURCE_CMD${NC}"
    fi
fi

echo -e "${GREEN}Shell completion setup complete!${NC}"
echo -e "${YELLOW}To enable completion in your current shell, run:${NC}"
echo -e "${BLUE}$SOURCE_CMD${NC}"
