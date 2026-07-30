#!/usr/bin/env bash
# promotion-image-preflight.sh — catch the "version-bump-on-main" trap before a Klever prod deploy.
#
# THE TRAP (2026-07-29 prod outage): a Klever app repo's `main` pipeline does NOT build an
# image — it only re-deploys an image that already exists in the approved registry. If you
# bump the version on `main` to a number no `dev` pipeline ever built (e.g. cherry-pick +
# version bump), `main` deploys a nonexistent image tag and prod 502s.
#
# This script answers the one question that prevents it:
#   "Does the approved registry already contain the exact image tag `main` is about to deploy?"
#
# GREEN  -> the tag exists; main can deploy it. (Optionally prints the digest for provenance.)
# RED    -> the tag does NOT exist. Do NOT play deploy-in-prod. You have two valid options:
#             1. Promote a dev version whose image was built by a dev pipeline (full dev->main).
#             2. Build a snapshot from a feature branch (KLEVER_DEPLOY_SNAPSHOT=prod), then deploy that tag.
#
# Usage:
#   promotion-image-preflight.sh --repo <path>                 # read version from the repo's version file
#   promotion-image-preflight.sh --repo <path> --version 1.1.87
#   promotion-image-preflight.sh --repo <path> --ref origin/main   # version from a specific ref
#   promotion-image-preflight.sh --image app-front-portal --version 1.1.87   # explicit image name
#
# Read-only. Requires `gcloud` authenticated with read on the approved registry.

# NB: no `set -e`/`pipefail` — version resolution deliberately TRIES multiple version files
# (package.json / pom.xml / pyproject) and expects most to fail per repo. `set -u` only.
set -u

REGISTRY="us-east1-docker.pkg.dev/prj-n-cmm-images-1bjvnygngl/are-usea1-docker-approved"

REPO="" ; VERSION="" ; REF="" ; IMAGE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2;;
    --version) VERSION="$2"; shift 2;;
    --ref) REF="$2"; shift 2;;
    --image) IMAGE="$2"; shift 2;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

# --- resolve the image name (defaults to the repo directory name = CI's ${CI_PROJECT_NAME}) ---
if [ -z "$IMAGE" ]; then
  [ -n "$REPO" ] || { echo "need --repo or --image" >&2; exit 2; }
  IMAGE="$(basename "$(cd "$REPO" && pwd)")"
fi

# --- resolve the version main would deploy ---
if [ -z "$VERSION" ]; then
  [ -n "$REPO" ] || { echo "need --version or --repo" >&2; exit 2; }
  # try package.json (Node), pom.xml (Java), pyproject.toml (Python) in that order
  vfile_val() {
    local path="$1" pat="$2"
    if [ -n "$REF" ]; then git -C "$REPO" show "$REF:$path" 2>/dev/null; else cat "$REPO/$path" 2>/dev/null; fi | eval "$pat"
  }
  VERSION="$(vfile_val package.json "grep -m1 '\"version\"' | sed -E 's/.*\"version\"[^\"]*\"([^\"]+)\".*/\1/'")"
  [ -z "$VERSION" ] && VERSION="$(vfile_val pom.xml "grep -m1 '<version>' | sed -E 's/.*<version>([^<]+)<.*/\1/'")"
  [ -z "$VERSION" ] && VERSION="$(vfile_val pyproject.toml "grep -m1 '^version' | sed -E 's/.*\"([^\"]+)\".*/\1/'")"
  [ -z "$VERSION" ] && { echo "could not read a version from $REPO (ref=${REF:-working tree}) — pass --version" >&2; exit 2; }
fi

echo "Preflight: $IMAGE  version=$VERSION"
echo "Registry:  $REGISTRY/$IMAGE"

DIGEST="$(gcloud artifacts docker tags list "$REGISTRY/$IMAGE" \
            --filter="tag:$VERSION" --format="value(version.basename())" 2>/dev/null | head -1 || true)"

if [ -n "$DIGEST" ]; then
  echo ""
  echo "✅ GREEN — image tag EXISTS in the approved registry."
  echo "   $IMAGE:$VERSION  ->  $DIGEST"
  echo "   main can deploy this. (Provenance: confirm the DAC plan resolves this exact tag/digest before apply.)"
  exit 0
else
  echo ""
  echo "🛑 RED — image tag $IMAGE:$VERSION does NOT exist in the approved registry."
  echo "   This is the version-bump-on-main trap. main does not BUILD; playing deploy-in-prod now → prod 502."
  echo ""
  echo "   Two valid paths:"
  echo "     1. Promote a dev version whose image a dev pipeline built (full dev→main)."
  echo "     2. Build a snapshot from a feature branch (KLEVER_DEPLOY_SNAPSHOT=prod), then deploy that snapshot tag."
  echo ""
  echo "   Recent tags that DO exist (pick a real one or build first):"
  gcloud artifacts docker tags list "$REGISTRY/$IMAGE" --format="value(tag.basename())" 2>/dev/null \
    | grep -E '^[0-9]' | sort -V | tail -6 | sed 's/^/     /'
  exit 1
fi
