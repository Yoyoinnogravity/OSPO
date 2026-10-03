#!/usr/bin/env bash
# =============================================================================
# Cursor-owned deploy to candooka.world  (Aled does not need PowerShell / SSH)
# =============================================================================
#
# Secret (one of these, from Cursor Cloud Agent environment secrets):
#   VPS_SSH_PASSWORD   root password for 159.198.66.11   ← usual choice
#   VPS_SSH_KEY        OpenSSH private key PEM (optional alternative)
#
# Command, from the repo root, after the secret is present:
#   ./_live_deploy/deploy.sh            # upload the live front-end set
#   ./_live_deploy/deploy.sh --check    # SSH whoami + ls only; no file changes
#
# Optional GitHub Action (same files, no PowerShell):
#   .github/workflows/deploy-candooka.yml  (workflow_dispatch)
#   GitHub repo secret of the same name: VPS_SSH_PASSWORD
#
# Will NOT touch:
#   users-db.json, users-db.json.bak, or any accounts database under api/
#
# Live set uploaded into /var/www/candooka/ (nginx:nginx):
#   index.html  style.css  style.min.css  app.js
# Cache-bust query params already live in index.html (?v= on css/js).
# =============================================================================
set -euo pipefail

HOST="${VPS_HOST:-159.198.66.11}"
USER="${VPS_USER:-root}"
WEB="${VPS_WEB:-/var/www/candooka}"
PORT="${VPS_PORT:-22}"

LIVE_FILES=(index.html style.css style.min.css app.js)
FORBIDDEN_PATTERNS=(users-db.json accounts)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_ONLY=0

usage() {
  sed -n '2,28p' "$0"
  exit "${1:-0}"
}

for arg in "$@"; do
  case "$arg" in
    --check|--dry-run|-n) CHECK_ONLY=1 ;;
    -h|--help) usage 0 ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage 1
      ;;
  esac
done

for f in "${LIVE_FILES[@]}"; do
  for bad in "${FORBIDDEN_PATTERNS[@]}"; do
    if [[ "$f" == *"$bad"* ]]; then
      echo "Refusing to deploy $f (matches $bad)" >&2
      exit 1
    fi
  done
  if [[ ! -f "$SCRIPT_DIR/$f" ]]; then
    echo "Missing local file: $SCRIPT_DIR/$f" >&2
    exit 1
  fi
done

KEY_FILE=""
cleanup() {
  if [[ -n "$KEY_FILE" && -f "$KEY_FILE" ]]; then
    rm -f "$KEY_FILE"
  fi
}
trap cleanup EXIT

SSH_OPTS=(
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=20
  -o NumberOfPasswordPrompts=1
  -o ServerAliveInterval=5
)

AUTH_PREFIX=()
if [[ -n "${VPS_SSH_KEY:-}" ]]; then
  KEY_FILE="$(mktemp)"
  chmod 600 "$KEY_FILE"
  printf '%s\n' "$VPS_SSH_KEY" > "$KEY_FILE"
  SSH_OPTS+=(-i "$KEY_FILE" -o IdentitiesOnly=yes -o PreferredAuthentications=publickey)
elif [[ -n "${VPS_SSH_PASSWORD:-}" ]]; then
  if ! command -v sshpass >/dev/null 2>&1; then
    echo "sshpass is required for password auth (apt-get install -y sshpass)" >&2
    exit 1
  fi
  export SSHPASS="$VPS_SSH_PASSWORD"
  AUTH_PREFIX=(sshpass -e)
  SSH_OPTS+=(-o PreferredAuthentications=password -o PubkeyAuthentication=no)
else
  cat >&2 <<'EOF'
No VPS credentials in this environment.

Paste the candooka.world root password ONCE as Cursor environment secret:
  VPS_SSH_PASSWORD

Cursor Cloud Agents → this environment → Secrets.
You do not need PowerShell and you do not need to SSH yourself.

Then rerun:
  ./_live_deploy/deploy.sh --check
  ./_live_deploy/deploy.sh
EOF
  exit 2
fi

ssh_cmd() {
  "${AUTH_PREFIX[@]}" ssh "${SSH_OPTS[@]}" -p "$PORT" "${USER}@${HOST}" "$@"
}

scp_cmd() {
  "${AUTH_PREFIX[@]}" scp "${SSH_OPTS[@]}" -P "$PORT" "$@"
}

echo "Connecting to ${USER}@${HOST}:${PORT} ..."
REMOTE_INFO="$(ssh_cmd 'echo "user=$(whoami) host=$(hostname) pwd=$(pwd)"; ls -l -- '"$WEB"'/index.html '"$WEB"'/style.css '"$WEB"'/style.min.css '"$WEB"'/app.js; echo "--- users-db (untouched, listing only) ---"; ls -l -- '"$WEB"'/api/users-db.json 2>/dev/null || echo "(no users-db.json visible — ok)"; echo "--- live cache-bust ---"; grep -oE "(style.min.css|app.js)[?]v=[0-9.]+" '"$WEB"'/index.html | sort -u')"
echo "$REMOTE_INFO"

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  echo
  echo "CHECK OK — no files were changed. users-db.json was not written."
  exit 0
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BK="/root/cursor-deploy-backup-${STAMP}"
STAGE="/tmp/candooka-deploy-${STAMP}"

echo "Backing up live files to ${BK} and staging upload in ${STAGE} ..."
ssh_cmd "mkdir -p '$BK' '$STAGE' && cp -a '$WEB/index.html' '$WEB/style.css' '$WEB/style.min.css' '$WEB/app.js' '$BK/' && echo Backup=$BK"

for f in "${LIVE_FILES[@]}"; do
  echo "Uploading $f"
  scp_cmd "$SCRIPT_DIR/$f" "${USER}@${HOST}:${STAGE}/$f"
done

ssh_cmd bash -s <<REMOTE
set -euo pipefail
WEB='$WEB'
STAGE='$STAGE'
BK='$BK'
# Never copy accounts DB — these four names only.
for f in index.html style.css style.min.css app.js; do
  if [[ "\$f" == *users-db* ]]; then
    echo "Refusing \$f" >&2
    exit 1
  fi
  install -m 644 "\$STAGE/\$f" "\$WEB/\$f"
done
if [[ -f "\$WEB/about.html" ]]; then
  chown --reference="\$WEB/about.html" \
    "\$WEB/index.html" "\$WEB/style.css" "\$WEB/style.min.css" "\$WEB/app.js" || true
elif id nginx >/dev/null 2>&1; then
  chown nginx:nginx "\$WEB/index.html" "\$WEB/style.css" "\$WEB/style.min.css" "\$WEB/app.js" || true
fi
rm -rf "\$STAGE"
echo DONE backup=\$BK
grep -oE '(style.min.css|app.js)[?]v=[0-9.]+' "\$WEB/index.html" | sort -u
ls -l "\$WEB/index.html" "\$WEB/style.css" "\$WEB/style.min.css" "\$WEB/app.js"
echo "users-db.json was not part of this deploy."
REMOTE

echo
echo "Deploy finished. Hard-refresh https://candooka.world if the browser still shows old ?v=."
