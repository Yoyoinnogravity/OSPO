# Candooka OSPO — agent instructions

Owner: **Aled Morgan**. Do not recut cryptic.fit / two-down films from this work.

## Number of Swaths

User-requested Number of Swaths is BINDING. Engagement/ranking MUST NOT rewrite N.

This is already documented in `_live_deploy/app.js` (comments on `_effectiveLinesPerSwath`, `_splitIntoSwathCount`, and 3D route mapping). Do not remove those comments, reintroduce ceil(n/N) empty-tail grouping that drops bands, or DP-permute swath order for a faster tour. The on-map N bands are the route.

A swath is a contiguous **across-track** band of neighbouring sail lines.
Map it with cyan dashed delimitation and a `SWATH n` label on that band.
Do not redefine a swath as a Low→High heading chip. Line colour is the
time rainbow.

Always-on Cursor rule: `.cursor/rules/swath-count-binding.mdc`

## Time-line colour

Time-line colour is BINDING and it is a **rainbow through time**. Red at
first acquisition, then orange, yellow, green, cyan, blue, violet at last,
mapped by elapsed survey time (not by line count). Sail lines, transits,
and the bottom timeline all use that clock.

Do not collapse it to a yellow wash, a single overview stroke, or a flat
green preplot. Show All must not duplicate every sail line on top of the
rainbow preplot (that hides swath delimitation). Step/focus still lights
the current line.

Always-on Cursor rule: `.cursor/rules/timeline-colours.mdc`

Guard: `node _live_deploy/test-route-solver.mjs` and `node _live_deploy/test-route-draw.mjs`

## Full-fold sq km

3D Prime Full Fold area is full-fold length × **(numStreamers × streamerSeparation / 2)**.
Aled already set this. Do not substitute preplot line spacing (adjacent sail-line
separation) or swath width. Line Separation in the summary is display / offline
only; it must not feed sq km.

Always-on Cursor rule: `.cursor/rules/sq-km-formula.mdc`
