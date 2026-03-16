#!/bin/bash
# TeamForge Seed Agent Installer
# Places the seed agent file and verifies prerequisites.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SEED_SOURCE="$SCRIPT_DIR/../seed.md"
TARGET_DIR="$HOME/.config/teamforge"
TARGET_FILE="$TARGET_DIR/seed.md"

echo "========================================"
echo "TeamForge Seed Agent Installer"
echo "========================================"
echo

# Create target directory if needed
if [ ! -d "$TARGET_DIR" ]; then
    mkdir -p "$TARGET_DIR"
    echo "Created $TARGET_DIR"
fi

# Copy seed file
if [ ! -f "$SEED_SOURCE" ]; then
    echo "ERROR: seed.md not found at $SEED_SOURCE"
    echo "Run this script from the crucible repository."
    exit 1
fi

if [ -f "$TARGET_FILE" ]; then
    SEED_ACTION="updated"
else
    SEED_ACTION="installed"
fi

cp "$SEED_SOURCE" "$TARGET_FILE"
echo "Seed agent $SEED_ACTION at $TARGET_FILE"

# Copy provisioning scripts
PROVISION_SH="$SCRIPT_DIR/provision_team.sh"
PROVISION_PY="$SCRIPT_DIR/provision_team.py"

if [ -f "$PROVISION_SH" ]; then
    cp "$PROVISION_SH" "$TARGET_DIR/provision_team.sh"
    chmod +x "$TARGET_DIR/provision_team.sh"
    echo "Provisioning script installed at $TARGET_DIR/provision_team.sh"
fi

if [ -f "$PROVISION_PY" ]; then
    cp "$PROVISION_PY" "$TARGET_DIR/provision_team.py"
    echo "Provisioning module installed at $TARGET_DIR/provision_team.py"
fi

# Check prerequisites
echo
echo "Checking prerequisites..."

PREREQS_OK=true

# Check credentials
if [ -f "$TARGET_DIR/credentials.json" ]; then
    echo "  [OK] credentials.json found"
else
    echo "  [WARN] credentials.json not found. Create it before using the seed agent."
    PREREQS_OK=false
fi

# Check gcloud
if command -v gcloud &> /dev/null; then
    echo "  [OK] gcloud CLI available"
else
    echo "  [WARN] gcloud CLI not found. Install it and run 'gcloud auth login'."
    PREREQS_OK=false
fi

# Check claude
if command -v claude &> /dev/null; then
    echo "  [OK] Claude Code CLI available"
else
    echo "  [WARN] Claude Code CLI not found. Install it to use the seed agent."
    PREREQS_OK=false
fi

if [ "$PREREQS_OK" = true ]; then
    echo
    echo "Prerequisites OK"
fi

# Print usage
echo
echo "========================================"
echo "Usage"
echo "========================================"
echo
echo "To provision a team on a new project:"
echo
echo "  Option A: Interactive (via seed agent)"
echo "    1. cd /path/to/your/new/project"
echo "    2. claude --agent ~/.config/teamforge/seed.md"
echo "    3. The seed agent will set everything up"
echo "    4. Start a new session with: claude"
echo
echo "  Option B: Script (from any session or terminal)"
echo "    1. cd /path/to/your/new/project"
echo "    2. bash ~/.config/teamforge/provision_team.sh [TEAM_SLUG]"
echo "    3. Start a new session with: claude"
echo
echo "  Either way, you're talking to the Team Lead."
echo
echo "Done."
