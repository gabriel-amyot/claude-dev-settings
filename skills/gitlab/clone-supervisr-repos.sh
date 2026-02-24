#!/bin/bash

# Clone all Supervisr.ai DAC and IAC repos from GitLab

set -e

echo "============================================"
echo "Cloning Supervisr.ai Repos from GitLab"
echo "============================================"
echo ""

BASE_URL="https://gitlab.prod.origin8cares.com"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

clone_repo() {
    local repo_url=$1
    local local_path=$2
    local repo_name=$(basename "$local_path")

    echo -e "${BLUE}→ Cloning: $repo_name${NC}"

    # Create parent directory if needed
    mkdir -p "$(dirname "$local_path")"

    if [ -d "$local_path/.git" ]; then
        echo -e "${GREEN}  ✓ Already cloned, updating...${NC}"
        cd "$local_path"
        git pull --quiet
        cd - > /dev/null
    else
        if git clone "$repo_url" "$local_path" 2>&1 | grep -q "fatal"; then
            echo -e "${RED}  ✗ Failed to clone${NC}"
            return 1
        else
            echo -e "${GREEN}  ✓ Cloned successfully${NC}"
        fi
    fi
}

# DAC Repos (under grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core)
echo -e "${BLUE}=== DAC Repos ===${NC}"
DAC_REPOS=(
    "https://gitlab.prod.origin8cares.com/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-auth0-manager.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-auth0-manager"
    "https://gitlab.prod.origin8cares.com/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-compliance-engine.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-compliance-engine"
    "https://gitlab.prod.origin8cares.com/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-eqs.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-eqs"
    "https://gitlab.prod.origin8cares.com/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-gateway-service.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-gateway-service"
    "https://gitlab.prod.origin8cares.com/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-retell-service.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-retell-service"
    "https://gitlab.prod.origin8cares.com/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-web-dashboard.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-web-dashboard"
    "https://gitlab.prod.origin8cares.com/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-web-ers.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-web-ers"
    "https://gitlab.prod.origin8cares.com/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-web-site.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/dac-sprvsr-core-web-site"
)

DAC_CLONED=0
DAC_FAILED=0

for repo_entry in "${DAC_REPOS[@]}"; do
    repo_url="${repo_entry%%|*}"
    local_path="${repo_entry##*|}"
    if clone_repo "$repo_url" "$local_path"; then
        ((DAC_CLONED++))
    else
        ((DAC_FAILED++))
    fi
done

echo ""
echo -e "${BLUE}=== IAC Repos ===${NC}"
IAC_REPOS=(
    "https://gitlab.prod.origin8cares.com/faas/grp-iac/grp-iac-sprvsr/iac-sprvsr-clarif.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-iac/grp-iac-sprvsr/iac-sprvsr-clarif"
    "https://gitlab.prod.origin8cares.com/faas/grp-iac/grp-iac-sprvsr/iac-sprvsr-core.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-iac/grp-iac-sprvsr/iac-sprvsr-core"
    "https://gitlab.prod.origin8cares.com/faas/grp-iac/grp-iac-sprvsr/iac-sprvsr-data.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-iac/grp-iac-sprvsr/iac-sprvsr-data"
    "https://gitlab.prod.origin8cares.com/faas/grp-iac/grp-iac-sprvsr/iac-sprvsr-sprvsr.git|/Users/gabrielamyot/Developer/supervisr-ai/faas/grp-iac/grp-iac-sprvsr/iac-sprvsr-sprvsr"
)

IAC_CLONED=0
IAC_FAILED=0

for repo_entry in "${IAC_REPOS[@]}"; do
    repo_url="${repo_entry%%|*}"
    local_path="${repo_entry##*|}"
    if clone_repo "$repo_url" "$local_path"; then
        ((IAC_CLONED++))
    else
        ((IAC_FAILED++))
    fi
done

# Summary
echo ""
echo "============================================"
echo -e "${GREEN}Summary${NC}"
echo "============================================"
echo -e "DAC Repos: ${GREEN}$DAC_CLONED cloned${NC}, ${RED}$DAC_FAILED failed${NC}"
echo -e "IAC Repos: ${GREEN}$IAC_CLONED cloned${NC}, ${RED}$IAC_FAILED failed${NC}"
echo ""
echo "Repos cloned to:"
echo "  DAC: /Users/gabrielamyot/Developer/supervisr-ai/faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/"
echo "  IAC: /Users/gabrielamyot/Developer/supervisr-ai/faas/grp-iac/grp-iac-sprvsr/"
