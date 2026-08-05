#!/usr/bin/env bash
#
# grant-local-components.sh — LOCAL DEV ONLY. Never deployed, never a Liquibase changeset.
#
# Why this exists:
#   The frontend's server-side component gate (app-front-portal lib/permissions/require-component.ts,
#   KTP-688 requireComponent) fails closed: it resolves the caller's User Management permissions and
#   403s unless the user holds the named component (or the sentinel "ALL" component). Newly gated API
#   routes (e.g. MediaPlanAgent for the media-plan agent) need that component granted. The committed
#   local UM seed (012-insert-local-test-data.sql) does NOT grant super-admins the "ALL" component,
#   so those gates 403 locally out of the box, and every `reseed` wipes any manual grant.
#
#   This script grants the "ALL" component to every ALL-scope (super administrator) permission in the
#   local UM database. That is the semantically correct local behavior — a super admin should see every
#   surface — and it is future-proof: any newly gated component passes locally without editing this
#   script. Idempotent: safe to re-run after every `reseed`.
#
# This is a LOCAL test-data mutation only. It must never be committed into a Liquibase changelog or
# applied to dev/uat/prod. It only touches the native local MySQL that start-stop-portal-in-local.sh
# provisions.
#
# Usage:
#   grant-local-components.sh            # apply the grant, print a summary
#   grant-local-components.sh --status   # show current super-admin component grants, change nothing
#   grant-local-components.sh --revert   # remove the ALL-component grant this script added
#
# Connection is mirrored from start-stop-portal-in-local.sh (native MySQL over unix socket).
# Override via env: MYSQL_PREFIX, MYSQL_DATADIR, DB_NAME.
set -euo pipefail

MYSQL_PREFIX="${MYSQL_PREFIX:-$(brew --prefix mysql@8.0 2>/dev/null || echo /opt/homebrew/opt/mysql@8.0)}"
MYSQL_DATADIR="${MYSQL_DATADIR:-$HOME/.klever-local-mysql/data}"
DB_NAME="${DB_NAME:-user_management_local}"
SOCK="$MYSQL_DATADIR/mysql.sock"

c_green=$'\033[0;32m'; c_yellow=$'\033[1;33m'; c_red=$'\033[0;31m'; c_off=$'\033[0m'
log()  { printf '%s[um-grant]%s %s\n' "$c_green"  "$c_off" "$*"; }
warn() { printf '%s[um-grant]%s %s\n' "$c_yellow" "$c_off" "$*"; }
err()  { printf '%s[um-grant]%s %s\n' "$c_red"    "$c_off" "$*" >&2; }

mysql_cli() { "$MYSQL_PREFIX/bin/mysql" --socket="$SOCK" -uroot "$@"; }

preflight() {
  [ -S "$SOCK" ] || { err "MySQL socket not found at $SOCK. Start the local stack first: start-stop-portal-in-local.sh start --profile backend"; exit 1; }
  mysql_cli -N -B -e "SELECT 1;" >/dev/null 2>&1 || { err "Cannot connect to local MySQL over $SOCK."; exit 1; }
  local has_tables
  has_tables="$(mysql_cli -N -B "$DB_NAME" -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME' AND table_name IN ('component','user_permission','user_component');" 2>/dev/null || echo 0)"
  [ "$has_tables" = "3" ] || { err "UM schema not present in $DB_NAME. Start User Management once (it builds the schema), then reseed."; exit 1; }
}

show_status() {
  log "Super-admin (ALL-scope) permissions and their components:"
  mysql_cli "$DB_NAME" -e "
    SELECT u.email, up.id AS permission_id,
           GROUP_CONCAT(c.name ORDER BY c.id SEPARATOR ', ') AS components
    FROM user_permission up
    JOIN user u ON u.id = up.user_id
    LEFT JOIN user_component uc ON uc.user_permission_id = up.id
    LEFT JOIN component c ON c.id = uc.component_id
    WHERE up.permission_type = 'ALL'
    GROUP BY u.email, up.id
    ORDER BY up.id;"
}

apply_grant() {
  preflight
  # Idempotent: only ALL-scope permissions that don't already hold the ALL component.
  local before after
  before="$(mysql_cli -N -B "$DB_NAME" -e "SELECT COUNT(*) FROM user_component uc JOIN component c ON c.id=uc.component_id WHERE c.name='ALL';")"
  mysql_cli "$DB_NAME" <<'SQL'
INSERT INTO user_component (component_id, user_permission_id)
SELECT c.id, up.id
FROM user_permission up
JOIN component c ON c.name = 'ALL'
WHERE up.permission_type = 'ALL'
  AND NOT EXISTS (
    SELECT 1 FROM user_component uc
    WHERE uc.user_permission_id = up.id
      AND uc.component_id = c.id
  );
SQL
  after="$(mysql_cli -N -B "$DB_NAME" -e "SELECT COUNT(*) FROM user_component uc JOIN component c ON c.id=uc.component_id WHERE c.name='ALL';")"
  local added=$(( after - before ))
  if [ "$added" -gt 0 ]; then
    log "Granted the ALL component to $added super-admin permission(s). Server-side component gates now pass locally."
  else
    log "No change — every ALL-scope permission already holds the ALL component."
  fi
  show_status
}

revert_grant() {
  preflight
  local removed
  removed="$(mysql_cli -N -B "$DB_NAME" -e "SELECT COUNT(*) FROM user_component uc JOIN component c ON c.id=uc.component_id JOIN user_permission up ON up.id=uc.user_permission_id WHERE c.name='ALL' AND up.permission_type='ALL';")"
  mysql_cli "$DB_NAME" <<'SQL'
DELETE uc FROM user_component uc
JOIN component c ON c.id = uc.component_id
JOIN user_permission up ON up.id = uc.user_permission_id
WHERE c.name = 'ALL' AND up.permission_type = 'ALL';
SQL
  warn "Removed the ALL-component grant from $removed super-admin permission(s). Gates will 403 again until re-applied."
}

case "${1:-}" in
  --status) preflight; show_status ;;
  --revert) revert_grant ;;
  ""|--apply) apply_grant ;;
  *) err "Unknown arg: $1"; echo "Usage: $0 [--apply|--status|--revert]" >&2; exit 2 ;;
esac
