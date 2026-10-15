/**
 * Guardrail: 3D swath shooting stays as Aled locked it.
 * Run: node scripts/test-3d-swath-lock.mjs
 *
 * Always asserts the Cursor rules / AGENTS.md text.
 * If _live_deploy/app.js is missing (this lock-in branch), planner asserts no-op.
 * If app.js is present, the same rules must still hold in source — fail on regression.
 */
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const appPath = join(root, '_live_deploy', 'app.js');
const swathRules = join(root, '.cursor', 'rules', '3d-swath-shooting.mdc');
const approvalRules = join(root, '.cursor', 'rules', 'aled-approval.mdc');
const agentsMd = join(root, 'AGENTS.md');

/** Locked pair-alternating default (0-based swath index). Do not "fix" join opposites. */
function expectedDefaultSwathDirection(i) {
  return Math.floor((i + 1) / 2) % 2 === 0 ? 'low-high' : 'high-low';
}

assert.deepEqual(
  [0, 1, 2, 3, 4, 5, 6, 7].map(expectedDefaultSwathDirection),
  ['low-high', 'high-low', 'high-low', 'low-high', 'low-high', 'high-low', 'high-low', 'low-high'],
  'pair-alternating spec drifted'
);

function mustExist(path) {
  assert.ok(existsSync(path), 'missing locked file: ' + path);
  return readFileSync(path, 'utf8');
}

const swathText = mustExist(swathRules);
const approvalText = mustExist(approvalRules);
const agentsText = mustExist(agentsMd);

assert.match(swathText, /alwaysApply:\s*true/, '3D swath rule must be always-on');
assert.match(approvalText, /alwaysApply:\s*true/, 'approval rule must be always-on');
assert.match(swathText, /neighbouring sail lines/);
assert.match(swathText, /Acquire per swath/);
assert.match(swathText, /heading on EVERY line in that swath/i);
assert.match(swathText, /Skip-k racetrack reverse is \*\*2D only\*\*/);
assert.match(swathText, /pair-alternating/);
assert.match(swathText, /swath joins/);
assert.match(swathText, /Math\.floor\(\(i \+ 1\) \/ 2\)/);
assert.match(swathText, /app\.js\?v=17\.23/);
assert.match(swathText, /36/);
assert.match(swathText, /37/);
assert.doesNotMatch(swathText, /^globs:/m, '3D swath rule must always apply, not only when editing app.js');

assert.match(approvalText, /Aled/);
assert.match(approvalText, /users-db/);
assert.match(approvalText, /account roles/);
assert.match(approvalText, /Survey Criteria 3D defaults/);
assert.match(approvalText, /deploy/i);
assert.match(approvalText, /Do not revert Aled's live role/);
assert.match(agentsText, /3d-swath-shooting\.mdc/);
assert.match(agentsText, /aled-approval\.mdc/);

function extractNamedFunction(src, name) {
  const start = src.search(new RegExp('function\\s+' + name + '\\s*\\('));
  if (start < 0) return null;
  const brace = src.indexOf('{', start);
  if (brace < 0) return null;
  let depth = 0;
  let inStr = null;
  let escape = false;
  for (let i = brace; i < src.length; i++) {
    const c = src[i];
    if (inStr) {
      if (escape) {
        escape = false;
        continue;
      }
      if (c === '\\') {
        escape = true;
        continue;
      }
      if (c === inStr) inStr = null;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') {
      inStr = c;
      continue;
    }
    if (c === '{') depth++;
    else if (c === '}') {
      depth--;
      if (depth === 0) return src.slice(start, i + 1);
    }
  }
  return null;
}

if (!existsSync(appPath)) {
  console.log('test-3d-swath-lock.mjs: rules locked; no app.js on this branch (ok)');
  process.exit(0);
}

const js = readFileSync(appPath, 'utf8');
function assertIn(src, re, msg) {
  assert.ok(re.test(src), msg);
}

assertIn(
  js,
  /surveyType === '3d' && progression === 'auto'[\s\S]{0,80}progression = 'interleaved'/,
  '3D Auto must remap to interleaved'
);
assertIn(js, /shoot each swath as a block/, 'must acquire each swath as a contiguous block');
assertIn(
  js,
  /never opposite directions on a swath/,
  'must lock one heading per swath (no opposite neighbours inside a swath)'
);
assertIn(
  js,
  /Skip-k reverse is 2D only|skip-k racetrack is 2D only|Auto TSP is 2D-only/i,
  'skip-k racetrack must stay 2D only'
);
assertIn(
  js,
  /swaths\.push\(indices\.slice\(g \* groupSize,\s*\(g \+ 1\) \* groupSize\)\)/,
  'swaths must be contiguous neighbouring-line bands'
);
assertIn(
  js,
  /for \(let g = 0; g < numSw; g\+?\+?\)[\s\S]{0,120}blockSeq\.push\(swaths\[g\]/,
  'default 3D walk is swaths 0,1,2… not skip-neighbour'
);

const dirSrc = extractNamedFunction(js, 'defaultSwathDirection');
assert.ok(dirSrc, 'defaultSwathDirection missing from app.js');
const defaultSwathDirection = new Function(`${dirSrc}\nreturn defaultSwathDirection;`)();
for (let i = 0; i < 10; i++) {
  assert.equal(
    defaultSwathDirection(i),
    expectedDefaultSwathDirection(i),
    'defaultSwathDirection(' + i + ') changed — do not fix swath-join opposites unless Aled asks'
  );
}

const planSrc = extractNamedFunction(js, 'planSwathBlockRacetracks');
if (planSrc) {
  assert.match(
    planSrc,
    /reversed:\s*rev/,
    'planSwathBlockRacetracks must use one heading for every line in the swath'
  );
  assert.doesNotMatch(
    planSrc,
    /reversed:\s*!rev/,
    'must not flip heading line-by-line inside a 3D swath'
  );

  const planSwathBlockRacetracks = new Function(
    `${planSrc}\nreturn planSwathBlockRacetracks;`
  )();
  const swaths = [
    [0, 1],
    [2, 3],
    [4, 5],
  ];
  const transitTimeSec = () => 1;
  const out = planSwathBlockRacetracks([], swaths, transitTimeSec, {
    swathDirs: ['low-high', 'high-low', 'low-high'],
  });
  assert.ok(out && Array.isArray(out.seq) && out.seq.length === 6, 'swath-block seq missing');
  assert.deepEqual(
    out.seq.map((s) => s.lineIdx),
    [0, 1, 2, 3, 4, 5],
    '3D Auto/interleaved must walk swaths 0,1,2… (not skip-neighbour 0,2,4 then 1,3,5)'
  );
  const revOf = (idx) => out.seq.find((s) => s.lineIdx === idx).reversed;
  assert.equal(revOf(0), false);
  assert.equal(revOf(1), false, 'both lines in swath 0 must share Low→High');
  assert.equal(revOf(2), true);
  assert.equal(revOf(3), true, 'both lines in swath 1 must share High→Low');
  assert.equal(revOf(4), false);
  assert.equal(revOf(5), false);
}

console.log('test-3d-swath-lock.mjs: ok (app.js invariants held)');
