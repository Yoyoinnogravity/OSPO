#!/usr/bin/env bash
# One-time macro: copy youtube-token.json into GitHub Actions, then merge the deploy PR.
# Run on your laptop (not in Cursor). Needs: gh auth login, repo admin, token file from twodown youtube-auth.
set -euo pipefail

REPO="${1:-Yoyoinnogravity/OSPO}"
TOKEN_FILE="${TWODOWN_YOUTUBE_TOKEN_FILE:-$HOME/.config/twodown/youtube-token.json}"
PR="${2:-50}"

if ! command -v gh >/dev/null; then
  echo "Install GitHub CLI: https://cli.github.com/" >&2
  exit 1
fi

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "Missing $TOKEN_FILE — run twodown youtube-auth first." >&2
  exit 1
fi

if ! python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('refresh_token') else 1)" "$TOKEN_FILE"; then
  echo "Token file has no refresh_token — run twodown youtube-auth again." >&2
  exit 1
fi

echo "Setting TWODOWN_YOUTUBE_TOKEN on $REPO …"
gh secret set TWODOWN_YOUTUBE_TOKEN --repo "$REPO" < "$TOKEN_FILE"

echo "Secret set. Merge PR #$PR? [y/N]"
read -r ans
if [[ "${ans,,}" == "y" ]]; then
  gh pr merge "$PR" --repo "$REPO" --squash --delete-branch=false
  echo "Merged. Enable Actions: $REPO → Actions → cryptic.fit daily → Run workflow (test)."
else
  echo "Skipped merge. Merge manually: https://github.com/$REPO/pull/$PR"
fi
