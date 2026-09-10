#!/bin/bash
# Deploy the on-map Labels / Annotations toggle (below PREPLOT SUMMARY).
# Does not touch users-db.json.
set -euo pipefail

WEB=/var/www/candooka
BK=/root/map-label-toggle-backup
BRANCH=cursor/map-label-toggle-a714
BASE="https://raw.githubusercontent.com/Yoyoinnogravity/OSPO/${BRANCH}/_live_deploy"

if [ ! -d "$WEB" ]; then
  echo "Cannot find $WEB — aborting"
  exit 1
fi

mkdir -p "$BK"
cp -a "$WEB/index.html" "$WEB/app.js" "$BK/" 2>/dev/null || true
echo "Backup in $BK"

curl -fsSL "$BASE/index.html" -o "$WEB/index.html"
curl -fsSL "$BASE/app.js" -o "$WEB/app.js"

echo DONE
ls -l "$WEB/index.html" "$WEB/app.js"
grep -o 'app.js?v=[0-9.]*' "$WEB/index.html" | head -1
