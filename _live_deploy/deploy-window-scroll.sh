#!/bin/bash
# Deploy menu fit/wrap + map/window scrollbars. Does not touch users-db.json.
set -euo pipefail

WEB=/var/www/candooka
BK=/root/window-scroll-backup
BRANCH=cursor/window-scroll-wrap-a4b0
BASE="https://raw.githubusercontent.com/Yoyoinnogravity/OSPO/${BRANCH}/_live_deploy"

if [ ! -d "$WEB" ]; then
  echo "Cannot find $WEB — aborting"
  exit 1
fi

mkdir -p "$BK"
cp -a "$WEB/index.html" "$WEB/style.css" "$WEB/style.min.css" "$WEB/app.js" "$BK/" 2>/dev/null || true
echo "Backup in $BK"

curl -fsSL "$BASE/index.html" -o "$WEB/index.html"
curl -fsSL "$BASE/style.css" -o "$WEB/style.css"
curl -fsSL "$BASE/style.min.css" -o "$WEB/style.min.css"
curl -fsSL "$BASE/app.js" -o "$WEB/app.js"

echo DONE
grep -o 'style.min.css?v=[0-9.]*' "$WEB/index.html" | head -1
grep -o 'app.js?v=[0-9.]*' "$WEB/index.html" | head -1
ls -l "$WEB/index.html" "$WEB/style.min.css" "$WEB/app.js"
