# Candooka OSPO — agent instructions

Owner: **Aled Morgan**. Do not change the product, live accounts, or candooka.world unless he explicitly asks in the current conversation.

Locked 3D swath rules: `.cursor/rules/3d-swath-shooting.mdc`  
Approval rule: `.cursor/rules/aled-approval.mdc`

If `_live_deploy/app.js` is present, run `node scripts/test-3d-swath-lock.mjs` before changing route planning. That test must keep passing. Do not weaken it to sneak in a new 3D tour.
