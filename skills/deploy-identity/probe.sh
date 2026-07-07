#!/usr/bin/env bash
# deploy-identity probe — the deterministic spine for KTP-688 hardening.
#
# Resolves "which branch/commit actually deploys" for a repo and compares it to the branch
# currently checked out (the code you are about to read/cite). Confidence is an OUTPUT computed
# from this resolution, NOT a self-rating.
#
# Usage:
#   probe.sh <path-inside-repo>            # path to a file or dir; repo is inferred
#   probe.sh --repo <repo-root>            # explicit repo root
#
# Output: human-readable lines, then a single machine-parseable line:
#   DEPLOY_IDENTITY_JSON={...}
# Exit code is ALWAYS 0 — this is a probe, not a gate. The hook decides whether to block.

set -u

REGISTRY_DIR="$HOME/.claude/deploy-identity"

# ---- resolve target path / repo root -------------------------------------------------
TARGET=""
REPO_ROOT=""
if [ "${1:-}" = "--repo" ]; then
  REPO_ROOT="${2:-}"
  TARGET="$REPO_ROOT"
else
  TARGET="${1:-$PWD}"
fi

# If TARGET is a file, start from its dir
PROBE_DIR="$TARGET"
[ -f "$PROBE_DIR" ] && PROBE_DIR="$(dirname "$PROBE_DIR")"
[ -d "$PROBE_DIR" ] || PROBE_DIR="$PWD"

if [ -z "$REPO_ROOT" ]; then
  REPO_ROOT="$(git -C "$PROBE_DIR" rev-parse --show-toplevel 2>/dev/null)"
fi

emit_json() { echo "DEPLOY_IDENTITY_JSON=$1"; }

if [ -z "$REPO_ROOT" ]; then
  echo "deploy-identity: not inside a git repo ($PROBE_DIR) — nothing to probe."
  emit_json '{"status":"NO_REPO","confidence":"UNKNOWN"}'
  exit 0
fi

REPO_BASENAME="$(basename "$REPO_ROOT")"

# ---- locate registry entry (harness-side first, then repo-local fallback) ------------
REG_FILE="$REGISTRY_DIR/$REPO_BASENAME.yaml"
if [ ! -f "$REG_FILE" ] && [ -f "$REPO_ROOT/.deploy-identity.yaml" ]; then
  REG_FILE="$REPO_ROOT/.deploy-identity.yaml"
fi

if [ ! -f "$REG_FILE" ]; then
  echo "deploy-identity: no registry entry for '$REPO_BASENAME' (looked in $REGISTRY_DIR and repo root)."
  echo "  → This repo has not opted into deploy-identity tracking. No deployed-branch claim can be verified here."
  emit_json "{\"status\":\"NO_REGISTRY\",\"confidence\":\"UNKNOWN\",\"repo\":\"$REPO_BASENAME\"}"
  exit 0
fi

# ---- parse flat key: value registry --------------------------------------------------
get() { sed -n "s/^$1:[[:space:]]*//p" "$REG_FILE" | head -1; }
DEPLOY_BRANCH="$(get deploy_branch)"
DEFAULT_BRANCH="$(get default_branch)"
OWNER="$(get owner)"
ARTIFACT_SOURCE="$(get artifact_source)"
DEPLOYED_TAG="$(get deployed_tag)"
DEPLOYED_SHA="$(get deployed_sha)"
CI_UNCONFIRMED="$(get ci_unconfirmed)"

[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH="$(git -C "$REPO_ROOT" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')"

# ---- current checked-out branch ------------------------------------------------------
CURRENT_BRANCH="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null)"
[ -z "$CURRENT_BRANCH" ] && CURRENT_BRANCH="(detached)"

# ---- resolve the deployed SHA --------------------------------------------------------
RESOLVED_SHA="$DEPLOYED_SHA"
SHA_SOURCE="cache"
# (live resolution intentionally not auto-run here: app-agent-hub is COS + nightly-down.
#  The skill documents how to refresh the cache when infra is reachable.)

# Normalise to a real commit if possible
FULL_SHA=""
if [ -n "$RESOLVED_SHA" ]; then
  FULL_SHA="$(git -C "$REPO_ROOT" rev-parse --verify "${RESOLVED_SHA}^{commit}" 2>/dev/null)"
fi

# ---- which branches contain the deployed commit -------------------------------------
CONTAINING=""
if [ -n "$FULL_SHA" ]; then
  CONTAINING="$(git -C "$REPO_ROOT" branch -r --contains "$FULL_SHA" 2>/dev/null | sed 's/^[* +]*//;s#^origin/##' | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
fi

# ---- WP-13: snapshot / unconfirmed-provenance signal --------------------------------
SNAPSHOT="false"
case "$DEPLOYED_TAG" in
  *-SNAPSHOT-*|*SNAPSHOT*) SNAPSHOT="true" ;;
esac
[ "$CI_UNCONFIRMED" = "true" ] && SNAPSHOT="true"

# ---- compare & compute status + confidence (the OUTPUT) ------------------------------
# Is the current branch one of the deploy branches?
ON_DEPLOY_BRANCH="false"
for b in $DEPLOY_BRANCH; do
  [ "$CURRENT_BRANCH" = "$b" ] && ON_DEPLOY_BRANCH="true"
done

# Does the current branch actually contain the deployed commit?
CURRENT_CONTAINS_DEPLOYED="unknown"
if [ -n "$FULL_SHA" ]; then
  if git -C "$REPO_ROOT" merge-base --is-ancestor "$FULL_SHA" HEAD 2>/dev/null; then
    CURRENT_CONTAINS_DEPLOYED="true"
  else
    CURRENT_CONTAINS_DEPLOYED="false"
  fi
fi

STATUS=""
CONFIDENCE=""
if [ "$ON_DEPLOY_BRANCH" = "true" ] && [ "$CURRENT_CONTAINS_DEPLOYED" != "false" ]; then
  STATUS="VERIFIED"
  CONFIDENCE="HIGH-ALLOWED"   # you are reading the deploy branch; HIGH confidence is permitted
elif [ -z "$FULL_SHA" ] && [ "$ON_DEPLOY_BRANCH" != "true" ]; then
  STATUS="CANT_VERIFY"
  CONFIDENCE="CANT_VERIFY"
else
  STATUS="MISMATCH"
  CONFIDENCE="HYPOTHESIS"     # you are NOT on the deploy branch — any deployed-code claim is a hypothesis
fi

# ---- citation stamp the agent should carry into any external/relayed claim -----------
if [ "$STATUS" = "VERIFIED" ]; then
  STAMP="[VERIFIED against ${DEPLOY_BRANCH}@${RESOLVED_SHA:-HEAD}]"
elif [ "$STATUS" = "MISMATCH" ]; then
  STAMP="[UNVERIFIED — read on ${CURRENT_BRANCH}, deploy=${DEPLOY_BRANCH}]"
else
  STAMP="[UNVERIFIED — deploy identity unresolved]"
fi

# ---- human-readable report -----------------------------------------------------------
echo "── deploy-identity probe: $REPO_BASENAME ──"
echo "  current branch (what you'd read/cite) : $CURRENT_BRANCH"
echo "  deploy branch  (what actually runs)   : ${DEPLOY_BRANCH:-?}"
echo "  default branch (origin/HEAD)          : ${DEFAULT_BRANCH:-?}"
echo "  deployed artifact                     : ${DEPLOYED_TAG:-?}  (sha ${RESOLVED_SHA:-?}, source $SHA_SOURCE)"
echo "  branches containing deployed commit   : ${CONTAINING:-unresolved}"
echo "  owner                                 : ${OWNER:-?}"
[ "$SNAPSHOT" = "true" ] && echo "  ⚠ WP-13: deployed artifact is a SNAPSHOT / CI-unconfirmed — provenance not pinned to a CI build."
echo "  STATUS = $STATUS    CONFIDENCE = $CONFIDENCE"
echo "  citation stamp → $STAMP"
if [ "$STATUS" = "MISMATCH" ]; then
  echo
  echo "  ‼ You are on '$CURRENT_BRANCH' but '${DEPLOY_BRANCH}' is what deploys."
  echo "    To reason about DEPLOYED behaviour, read the deploy branch directly, e.g.:"
  echo "      git -C $REPO_ROOT show ${DEPLOY_BRANCH}:<relative/path>"
  echo "      git -C $REPO_ROOT grep <pattern> ${DEPLOY_BRANCH}"
  echo "    Do NOT cite line numbers / prompts / logic from '$CURRENT_BRANCH' as if deployed."
fi

# ---- machine-parseable line ----------------------------------------------------------
emit_json "{\"status\":\"$STATUS\",\"confidence\":\"$CONFIDENCE\",\"repo\":\"$REPO_BASENAME\",\"current_branch\":\"$CURRENT_BRANCH\",\"deploy_branch\":\"$DEPLOY_BRANCH\",\"default_branch\":\"$DEFAULT_BRANCH\",\"deployed_sha\":\"${RESOLVED_SHA:-}\",\"deployed_tag\":\"${DEPLOYED_TAG:-}\",\"on_deploy_branch\":$ON_DEPLOY_BRANCH,\"snapshot\":$SNAPSHOT,\"owner\":\"${OWNER:-}\",\"stamp\":\"$STAMP\"}"
exit 0
