# Candooka OSPO — agent instructions

Owner: **Aled Morgan**. Do not recut cryptic.fit / two-down films from this work.

## Number of Swaths

User-requested Number of Swaths is BINDING. Engagement/ranking MUST NOT rewrite N.

This is already documented in `_live_deploy/app.js` (comments on `_effectiveLinesPerSwath`, `_splitIntoSwathCount`, and 3D Auto DP). Do not remove those comments or reintroduce ceil(n/N) empty-tail grouping that drops bands.

Always-on Cursor rule: `.cursor/rules/swath-count-binding.mdc`

Guard: `node _live_deploy/test-route-solver.mjs`
