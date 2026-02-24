#!/bin/bash
# GitLab Skill - Quick Setup Script

set -e

SKILL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SETUP_SCRIPT="$SKILL_DIR/gitlab_config_setup.py"

echo "======================================"
echo "GitLab Skill - Initial Setup"
echo "======================================"
echo ""

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not installed"
    exit 1
fi

# Check if requests module is available
if ! python3 -c "import requests" 2>/dev/null; then
    echo "Warning: 'requests' module not found. Installing..."
    pip3 install requests
fi

echo "Configuring GitLab credentials for your organizations..."
echo ""

# Configure each organization
for org in klever origin8 supervisrai; do
    echo "---"
    echo "Setting up: $org"
    echo "---"
    python3 "$SETUP_SCRIPT" configure "$org"
    echo ""
done

# Set default org
echo "---"
echo "Setting default organization..."
echo "---"
read -p "Enter default organization (klever/origin8/supervisrai) [supervisrai]: " default_org
default_org=${default_org:-supervisrai}

python3 "$SETUP_SCRIPT" default "$default_org"
echo ""

# List all configs
echo "======================================"
echo "Configuration Complete!"
echo "======================================"
echo ""
python3 "$SETUP_SCRIPT" list

echo ""
echo "You're all set! Try these commands:"
echo ""
echo "List all groups in default organization:"
echo "  python3 $SKILL_DIR/gitlab_skill.py list-groups"
echo ""
echo "List repos in a group:"
echo "  python3 $SKILL_DIR/gitlab_skill.py list-repos --group f-r-r-s --full"
echo ""
echo "Clone all repos from a group:"
echo "  python3 $SKILL_DIR/gitlab_skill.py clone --group f-r-r-s"
echo ""
echo "For more information, see: $SKILL_DIR/README.md"
