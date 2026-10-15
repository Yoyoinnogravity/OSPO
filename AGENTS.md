# Candooka OSPO — agent instructions

Owner: **Aled Morgan** (Designer). Do not change the product, live accounts, Survey Criteria 3D defaults, or candooka.world unless he explicitly asks in the current conversation.

Always-on Cursor rules (read these; they are not optional):

- 3D shooting: `.cursor/rules/3d-swath-shooting.mdc`
- Approval gate: `.cursor/rules/aled-approval.mdc`

Regression guard: `node scripts/test-3d-swath-lock.mjs`  
It always checks the locked rules. If `_live_deploy/app.js` is present it also asserts planner invariants (3D Auto → interleaved block walk, one heading per swath, pair-alternating defaults, skip-k is 2D only). Do not weaken that test to sneak in a new tour.

Do not change route-planner behaviour unless Aled asked for a planner change. Live site is still `app.js?v=17.23`. Draft PRs 36/37 are not deployed.
