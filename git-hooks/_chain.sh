#!/bin/bash
# Chain to a repository's own hook of the same name.
#
# WHY THIS EXISTS
#     core.hooksPath REPLACES .git/hooks entirely, it does not layer on top.
#     Setting it globally without chaining would silently disable every existing
#     per-repo hook. app-proximity-report and app-front-portal both carry
#     graphify post-commit/post-checkout hooks that rebuild the knowledge graph;
#     those would have stopped firing with no error and no warning.
#
#     Silent breakage of someone else's tooling is the worst possible outcome of
#     a "safety" feature, so every global hook ends by calling this.
#
# Usage (last line of a global hook):  . "$(dirname "$0")/_chain.sh"

_chain_hook_name="$(basename "$0")"
_chain_git_dir="$(git rev-parse --git-dir 2>/dev/null)" || exit 0
_chain_local="${_chain_git_dir}/hooks/${_chain_hook_name}"

if [ -x "$_chain_local" ]; then
    exec "$_chain_local" "$@"
fi
exit 0
