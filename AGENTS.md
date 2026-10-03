# Candooka OSPO — agent instructions

Owner: **Aled Morgan**. Do not recut cryptic.fit / two-down films from this work.

## Number of Swaths

User-requested Number of Swaths is BINDING. Engagement/ranking MUST NOT rewrite N.

This is already documented in `_live_deploy/app.js` (comments on `_effectiveLinesPerSwath`, `_splitIntoSwathCount`, and 3D route mapping). Do not remove those comments, reintroduce ceil(n/N) empty-tail grouping that drops bands, or DP-permute swath order for a faster tour. The on-map N bands are the route.

Always-on Cursor rule: `.cursor/rules/swath-count-binding.mdc`

## Time-line colour

Time-line colour is BINDING. Red at first acquisition, green at last. The
planned route overlay and the bottom timeline bar must both show that
sequence. Do not flatten transits, run-out, or the timeline to a single
yellow/overview stroke for "readability" or engagement.

Always-on Cursor rule: `.cursor/rules/timeline-colours.mdc`

Guard: `node _live_deploy/test-route-solver.mjs` and `node _live_deploy/test-route-draw.mjs`

## Full-fold sq km

3D Prime Full Fold area is line km × **preplot line separation** (adjacent sail
lines on the grid). Do not use `(streamers × sep) / 2` or swath width.
