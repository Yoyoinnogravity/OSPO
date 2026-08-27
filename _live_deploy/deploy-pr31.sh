#!/bin/bash
# Deploy PR #31 login-recovery files onto the live Candooka web root.
# Does not touch users-db.json.
set -euo pipefail

WEB=/var/www/candooka
BK=/root/pr31-backup
BRANCH=cursor/restore-user-logins-a714
BASE="https://raw.githubusercontent.com/Yoyoinnogravity/OSPO/${BRANCH}/_live_deploy"

if [ ! -d "$WEB/api" ]; then
  echo "Cannot find $WEB/api — aborting"
  exit 1
fi

mkdir -p "$BK/api"
cp -a "$WEB"/api/*.php "$BK/api/" 2>/dev/null || true
cp -a "$WEB/index.html" "$WEB/app.js" "$BK/" 2>/dev/null || true
echo "Backup in $BK"

fetch() {
  local rel="$1"
  local dest="$WEB/$rel"
  echo "Fetching $rel"
  curl -fsSL "$BASE/$rel" -o "$dest"
}

fetch api/_users_lib.php
fetch api/auth-login.php
fetch api/users.php
fetch api/login-logs.php
fetch api/login-notify.php
fetch api/trial-signup.php
fetch index.html
fetch app.js

if [ -f "$WEB/api/sst.php" ]; then
  chown --reference="$WEB/api/sst.php" \
    "$WEB/api/_users_lib.php" \
    "$WEB/api/auth-login.php" \
    "$WEB/api/users.php" \
    "$WEB/api/login-logs.php" \
    "$WEB/api/login-notify.php" \
    "$WEB/api/trial-signup.php" || true
fi

echo DONE
ls -l "$WEB/api/_users_lib.php" "$WEB/api/auth-login.php" "$WEB/api/users.php" "$WEB/index.html" "$WEB/app.js"
