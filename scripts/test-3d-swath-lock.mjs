/**
 * Guardrail: 3D swath shooting stays as Aled locked it.
 * Run: node scripts/test-3d-swath-lock.mjs
 * Skips code assertions when _live_deploy/app.js is not on this branch.
 */
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const app = join(root, '_live_deploy', 'app.js');
const rules = [
  join(root, '.cursor', 'rules', '3d-swath-shooting.mdc'),
  join(root, '.cursor', 'rules', 'aled-approval.mdc'),
];

for (const f of rules) {
  assert.ok(existsSync(f), 'missing locked rule file: ' + f);
  const t = readFileSync(f, 'utf8');
  assert.match(t, /Aled/, f + ' must name Aled');
}

if (!existsSync(app)) {
  console.log('test-3d-swath-lock.mjs: rules present; no app.js on this branch (ok)');
  process.exit(0);
}

const js = readFileSync(app, 'utf8');
assert.match(js, /function planSwathBlockRacetracks/);
assert.match(js, /one heading for every line in that swath|swathDirs/);
assert.match(js, /Skip-k reverse is 2D only|skip-k racetrack is 2D only|2D-only/i);
assert.doesNotMatch(
  js,
  /function planSwathBlockRacetracks[\s\S]{0,800}reversed:\s*!rev/,
  'must not flip heading line-by-line inside a 3D swath'
);
console.log('test-3d-swath-lock.mjs: ok (app.js invariants held)');
