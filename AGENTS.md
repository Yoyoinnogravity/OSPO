# Candooka OSPO — agent instructions

Owner: **Aled Morgan**. Do not recut cryptic.fit / two-down films from this work.

## Number of Swaths

User-requested Number of Swaths is BINDING. Engagement/ranking MUST NOT rewrite N.

This is already documented in `_live_deploy/app.js` (comments on `_effectiveLinesPerSwath`, `_splitIntoSwathCount`, and 3D route mapping). Do not remove those comments, reintroduce ceil(n/N) empty-tail grouping that drops bands, or DP-permute swath order for a faster tour. The on-map N bands are the route.

Always-on Cursor rule: `.cursor/rules/swath-count-binding.mdc`

Guard: `node _live_deploy/test-route-solver.mjs`
