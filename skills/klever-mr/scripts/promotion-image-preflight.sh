#!/usr/bin/env bash
# promotion-image-preflight.sh — catch the "version-bump-on-main" trap before a Klever prod deploy.
#
# THE TRAP (2026-07-29 prod outage): a Klever app repo's `main` pipeline does NOT build an
# artifact. It only re-deploys an artifact that a `dev` pipeline already published. If `main`
# carries a version no `dev` pipeline ever built, `main` deploys a nonexistent artifact and prod fails.
#
# This script answers one question:
#   "Does the artifact that `main` is about to deploy already exist?"
#
# It detects the artifact type from the promoted revision's .gitlab-ci.yml:
#   image  -> datasophia-glb-incl-build-docker   -> tag in the approved Docker registry
#   zip    -> datasophia-glb-incl-zip-artifact   -> gs://<bucket>/<name>/zip/<name>_<version>.zip
# For a zip repo the version comes from DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION, because that
# variable (not the version file) names the artifact.
#
# Exit codes (the verdict is the exit code, not the text):
#   0 GREEN        the artifact exists; main can deploy it.
#   1 RED          the lookup ran and the artifact is absent. Do NOT play deploy-in-prod.
#   2 usage error
#   3 CANT_VERIFY  the type is ambiguous, or the lookup failed (auth, wrong name, network).
#                  This is NOT a missing artifact. Fix the cause and re-run.
#
# Usage:
#   promotion-image-preflight.sh --repo <path> [--ref origin/main]   # detect type + version
#   promotion-image-preflight.sh --repo <path> --version 1.1.87
#   promotion-image-preflight.sh --image app-front-portal --version 1.1.87   # explicit image
#   promotion-image-preflight.sh --repo <path> --type zip                    # force the type
#
# Read-only. Requires `gcloud` authenticated with read on the registry or the artifact bucket.

# No `set -e`: version resolution tries several version files and expects most to fail.
set -u

REGISTRY="us-east1-docker.pkg.dev/prj-n-cmm-images-1bjvnygngl/are-usea1-docker-approved"
DEFAULT_ZIP_BUCKET="bkt-atfhst-1bjvnygngl"

REPO="" ; VERSION="" ; REF="" ; IMAGE="" ; TYPE="auto"
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2;;
    --version) VERSION="$2"; shift 2;;
    --ref) REF="$2"; shift 2;;
    --image) IMAGE="$2"; shift 2;;
    --type) TYPE="$2"; shift 2;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

case "$TYPE" in auto|image|zip) ;; *) echo "--type must be auto, image or zip" >&2; exit 2;; esac
[ -n "$REPO" ] || [ -n "$IMAGE" ] || { echo "need --repo or --image" >&2; exit 2; }

cant_verify() {
  echo ""
  echo "CANT_VERIFY — $1"
  echo "   This is not a missing artifact. The check did not run to completion."
  [ -n "${2:-}" ] && echo "   $2"
  exit 3
}

read_repo_file() {
  local path="$1"
  if [ -n "$REF" ]; then git -C "$REPO" show "$REF:$path" 2>/dev/null; else cat "$REPO/$path" 2>/dev/null; fi
}

ci_var() {
  printf '%s\n' "$CI_TEXT" \
    | grep -m1 -E "^[[:space:]]*$1[[:space:]]*:" \
    | sed -E "s/^[^:]*:[[:space:]]*//; s/[[:space:]]+#.*$//; s/^[\"']//; s/[\"'][[:space:]]*$//"
}

repo_name() {
  local url
  url="$(git -C "$REPO" remote get-url origin 2>/dev/null)"
  if [ -n "$url" ]; then basename "$url" .git; else basename "$(cd "$REPO" && pwd)"; fi
}

# --- detect the artifact type from the promoted revision ---
CI_TEXT=""
[ -n "$REPO" ] && CI_TEXT="$(read_repo_file .gitlab-ci.yml)"
if [ "$TYPE" = "auto" ]; then
  HAS_ZIP=0 ; HAS_IMAGE=0
  printf '%s\n' "$CI_TEXT" | grep -qE 'datasophia-glb-incl-zip-artifact|DATASOPHIA_INCL_ZIP_ARTIFACT_' && HAS_ZIP=1
  printf '%s\n' "$CI_TEXT" | grep -qE 'datasophia-glb-incl-build-docker|DATASOPHIA_INCL_BUILD_DOCKER_' && HAS_IMAGE=1
  if [ "$HAS_ZIP" = 1 ] && [ "$HAS_IMAGE" = 0 ]; then TYPE="zip"
  elif [ "$HAS_IMAGE" = 1 ] && [ "$HAS_ZIP" = 0 ]; then TYPE="image"
  elif [ -n "$IMAGE" ] && [ -z "$REPO" ]; then TYPE="image"
  else
    cant_verify "artifact type is ambiguous (zip markers: $HAS_ZIP, docker markers: $HAS_IMAGE) in .gitlab-ci.yml at ${REF:-working tree}." \
      "Pass --type image or --type zip after you read the repo's CI includes."
  fi
fi

# --- zip artifact path ---
if [ "$TYPE" = "zip" ]; then
  [ -n "$REPO" ] || { echo "--type zip needs --repo" >&2; exit 2; }
  NAME="$(ci_var DATASOPHIA_INCL_ZIP_ARTIFACT_NAME)"
  case "$NAME" in ""|*'$'*) NAME="$(repo_name)";; esac
  BUCKET="$(ci_var DATASOPHIA_INCL_ZIP_ARTIFACT_DESTINATION_BUCKET)"
  [ -n "$BUCKET" ] || BUCKET="$DEFAULT_ZIP_BUCKET"
  CI_VERSION="$(ci_var DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION)"
  [ -n "$VERSION" ] || VERSION="$CI_VERSION"
  [ -n "$VERSION" ] || cant_verify "no DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION in .gitlab-ci.yml at ${REF:-working tree}." "Pass --version."
  PREFIX="gs://$BUCKET/$NAME/zip/"
  OBJECT="${PREFIX}${NAME}_${VERSION}.zip"
  echo "Preflight: zip artifact  $NAME  version=$VERSION"
  echo "Location:  $OBJECT"
  ERR="$(mktemp)"
  LISTING="$(gcloud storage ls "$PREFIX" 2>"$ERR")"; RC=$?
  if [ $RC -ne 0 ]; then
    MSG="$(head -3 "$ERR" | tr '\n' ' ')"; rm -f "$ERR"
    cant_verify "gcloud storage ls $PREFIX failed (exit $RC): $MSG" "If it asks to reauthenticate, run 'gcloud auth login' and re-run."
  fi
  rm -f "$ERR"
  if printf '%s\n' "$LISTING" | grep -Fxq "$OBJECT"; then
    echo ""
    echo "GREEN — the zip artifact EXISTS. main can deploy it."
    exit 0
  fi
  echo ""
  echo "RED — $OBJECT does NOT exist."
  echo "   main does not build zip artifacts (only dev sets BUILD_UPLOAD)."
  echo "   Merge to dev first with the version bumped in BOTH the version file and"
  echo "   DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION, let the dev pipeline upload, then promote."
  echo ""
  echo "   Recent artifacts that DO exist:"
  printf '%s\n' "$LISTING" | grep -E '\.zip$' | sort -V | tail -6 | sed 's/^/     /'
  exit 1
fi

# --- Docker image path ---
[ -n "$IMAGE" ] || IMAGE="$(repo_name)"
if [ -z "$VERSION" ]; then
  [ -n "$REPO" ] || { echo "need --version or --repo" >&2; exit 2; }
  VERSION="$(read_repo_file package.json | grep -m1 '"version"' | sed -E 's/.*"version"[^"]*"([^"]+)".*/\1/')"
  [ -z "$VERSION" ] && VERSION="$(read_repo_file pom.xml | grep -m1 '<version>' | sed -E 's/.*<version>([^<]+)<.*/\1/')"
  [ -z "$VERSION" ] && VERSION="$(read_repo_file pyproject.toml | grep -m1 '^version' | sed -E 's/.*"([^"]+)".*/\1/')"
  [ -z "$VERSION" ] && { echo "could not read a version from $REPO (ref=${REF:-working tree}). Pass --version." >&2; exit 2; }
fi

echo "Preflight: image  $IMAGE  version=$VERSION"
echo "Registry:  $REGISTRY/$IMAGE"
ERR="$(mktemp)"
TAGS="$(gcloud artifacts docker tags list "$REGISTRY/$IMAGE" --format="value(tag.basename(),version.basename())" 2>"$ERR")"; RC=$?
if [ $RC -ne 0 ]; then
  MSG="$(head -3 "$ERR" | tr '\n' ' ')"; rm -f "$ERR"
  cant_verify "gcloud artifacts docker tags list failed (exit $RC): $MSG" "If it asks to reauthenticate, run 'gcloud auth login' and re-run."
fi
rm -f "$ERR"
if [ -z "$(printf '%s' "$TAGS" | tr -d '[:space:]')" ]; then
  cant_verify "the registry returned zero tags for $IMAGE." \
    "A live image repo always has tags. Check the image name, or whether this repo ships a zip artifact (--type zip)."
fi

DIGEST="$(printf '%s\n' "$TAGS" | awk -v v="$VERSION" '$1 == v { print $2; exit }')"
if printf '%s\n' "$TAGS" | awk -v v="$VERSION" '$1 == v { found = 1 } END { exit !found }'; then
  echo ""
  echo "GREEN — image tag EXISTS in the approved registry."
  echo "   $IMAGE:$VERSION  ->  ${DIGEST:-digest not shown}"
  echo "   main can deploy this. Confirm the DAC plan resolves this exact tag before apply."
  exit 0
fi
echo ""
echo "RED — image tag $IMAGE:$VERSION does NOT exist in the approved registry."
echo "   This is the version-bump-on-main trap. main does not BUILD. Playing deploy-in-prod now -> prod 502."
echo ""
echo "   Two valid paths:"
echo "     1. Promote a dev version whose image a dev pipeline built (full dev->main)."
echo "     2. Build a snapshot from a feature branch (KLEVER_DEPLOY_SNAPSHOT=prod), then deploy that snapshot tag."
echo ""
echo "   Recent tags that DO exist:"
printf '%s\n' "$TAGS" | awk '{ print $1 }' | grep -E '^[0-9]' | sort -V | tail -6 | sed 's/^/     /'
exit 1
