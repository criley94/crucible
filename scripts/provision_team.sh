#!/bin/bash
# TeamForge Team Provisioning Script
#
# Provisions a TeamForge team onto the current project by generating
# CLAUDE.md, .claude/agents/*.md, and .claude/settings.local.json.
#
# Usage:
#   bash provision_team.sh [TEAM_SLUG]
#
# If TEAM_SLUG is omitted, reads the default from ~/.config/teamforge/credentials.json.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/provision_team.py"

# If the python script isn't next to us, check the installed location
if [ ! -f "$PYTHON_SCRIPT" ]; then
    PYTHON_SCRIPT="$HOME/.config/teamforge/provision_team.py"
fi

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "ERROR: provision_team.py not found."
    echo "Expected at: $SCRIPT_DIR/provision_team.py"
    echo "       or at: $HOME/.config/teamforge/provision_team.py"
    exit 1
fi

TEAM_ARG=""
if [ -n "$1" ]; then
    TEAM_ARG="--team $1"
fi

python3 "$PYTHON_SCRIPT" $TEAM_ARG --target-dir "$(pwd)"
