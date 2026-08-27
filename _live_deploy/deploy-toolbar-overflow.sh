#!/bin/bash
# Deploy toolbar wrap / scale / scrollbar fix. Does not touch users-db.json.
set -euo pipefail

WEB=/var/www/candooka
BK=/root/toolbar-overflow-backup
BRANCH=cursor/toolbar-overflow-a714
BASE="https://raw.githubusercontent.com/Yoyoinnogravity/OSPO/${BRANCH}/_live_deploy"

if [ ! -d "$WEB" ]; then
  echo "Cannot find $WEB — aborting"
  exit 1
fi

mkdir -p "$BK"
cp -a "$WEB/index.html" "$WEB/app.js" "$WEB/style.css" "$WEB/style.min.css" "$BK/" 2>/dev/null || true
echo "Backup in $BK"

curl -fsSL "$BASE/index.html" -o "$WEB/index.html"
curl -fsSL "$BASE/app.js" -o "$WEB/app.js"
curl -fsSL "$BASE/style.css" -o "$WEB/style.css"
curl -fsSL "$BASE/style.min.css" -o "$WEB/style.min.css"

echo DONE
grep -oE 'style.min.css\?v=[0-9.]+|app.js\?v=[0-9.]+' "$WEB/index.html"
ls -l "$WEB/index.html" "$WEB/app.js" "$WEB/style.min.css"
