#!/usr/bin/env node
/**
 * Visit-sequence quality for the marine survey route planner.
 * Parallel 164-line preplots must be a skip-k racetrack (turn-radius
 * U-turns at the line ends), not a nearest-neighbour / 2-opt hairball.
 */
import fs from 'fs';
import vm from 'vm';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(path.resolve(__dirname, 'app.js'), 'utf8');

function elStub(id) {
  return {
    id, style: {}, value: '', textContent: '', innerHTML: '', checked: false,
    classList: { add() {}, remove() {}, contains() { return false; }, toggle() {} },
    addEventListener() {}, removeEventListener() {}, appendChild() {},
    remove() {}, querySelector() { return elStub('q'); }, querySelectorAll() { return []; },
    getBoundingClientRect() { return { top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 }; },
    focus() {}, select() {}, click() {}, setAttribute() {}, getAttribute() { return null; },
    children: [], parentNode: { removeChild() {} }, dataset: {},
  };
}

const document = {
  readyState: 'loading',
  body: { appendChild() {}, removeChild() {}, style: {} },
  documentElement: { style: {} },
  addEventListener() {},
  removeEventListener() {},
  createElement: (tag) => elStub(tag),
  getElementById: () => elStub('x'),
  querySelector() { return elStub('q'); },
  querySelectorAll() { return []; },
};

const window = {
  document,
  addEventListener() {},
  removeEventListener() {},
  innerWidth: 1400,
  innerHeight: 900,
  devicePixelRatio: 1,
  localStorage: { _s: {}, getItem() { return null; }, setItem() {}, removeItem() {} },
};

const mapStub = {
  setView() { return this; },
  addLayer() { return this; },
  removeLayer() { return this; },
  on() { return this; },
  off() { return this; },
  fitBounds() { return this; },
  getBounds() { return { pad() { return this; }, getSouthWest() { return { lat: 0, lng: 0 }; }, getNorthEast() { return { lat: 1, lng: 1 }; } }; },
  getContainer() { return elStub('map'); },
  invalidateSize() {},
};

const ctx = {
  window, document, console,
  setTimeout, clearTimeout, setInterval, clearInterval,
  localStorage: window.localStorage,
  fetch: async () => ({ json: async () => ({}), ok: false, status: 404 }),
  alert() {},
  L: {
    map() { return mapStub; },
    tileLayer() { return { addTo() { return this; }, on() { return this; } }; },
    layerGroup() { return { addTo() { return this; }, clearLayers() {}, addLayer() {} }; },
    polyline() { return { addTo() { return this; }, setStyle() { return this; } }; },
    marker() { return { addTo() { return this; }, bindTooltip() { return this; } }; },
    divIcon() { return {}; },
    latLngBounds() { return { extend() {}, pad() { return this; } }; },
    DomEvent: { disableScrollPropagation() {}, disableClickPropagation() {} },
  },
  MutationObserver: class { observe() {} disconnect() {} },
  Node: function () {},
  HTMLElement: function () {},
  navigator: { userAgent: 'node' },
  location: { href: 'http://localhost/' },
  URL,
  Blob: class {},
  FileReader: class {},
  atob, btoa,
  XMLHttpRequest: class {
    open() {}
    setRequestHeader() {}
    send() { this.status = 404; this.responseText = ''; }
  },
};
ctx.global = ctx;
ctx.self = ctx;
ctx.window = window;
window.window = window;
window.document = document;
ctx.globalThis = ctx;

vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'app.js' });
vm.runInContext(`
  if (typeof showToast !== 'function') showToast = function(){};
  else { const _t = showToast; showToast = function(){}; }
`, ctx);

function makeGrid(n, spacingM = 250, lengthM = 20000) {
  const lat0 = -20.5, lon0 = 110.2;
  const mLat = 111320;
  const mLon = 111320 * Math.cos(lat0 * Math.PI / 180);
  const lines = [];
  for (let i = 0; i < n; i++) {
    const east = i * spacingM;
    const dlon = east / mLon;
    const dlat = lengthM / mLat;
    lines.push({
      id: i,
      name: 'L' + (1000 + i),
      start: [lat0, lon0 + dlon],
      end: [lat0 + dlat, lon0 + dlon],
    });
  }
  return lines;
}

function spatialIndex(lines, order) {
  const midLon = lines.map(l => (l.start[1] + l.end[1]) / 2);
  const sorted = lines.map((_, i) => i).sort((a, b) => midLon[a] - midLon[b]);
  const rank = new Array(lines.length);
  sorted.forEach((li, r) => { rank[li] = r; });
  return order.map(o => rank[o.lineIdx]);
}

function skipStats(ranks) {
  const skips = [];
  const deltas = [];
  for (let i = 1; i < ranks.length; i++) {
    deltas.push(ranks[i] - ranks[i - 1]);
    skips.push(Math.abs(ranks[i] - ranks[i - 1]));
  }
  const mean = skips.reduce((a, b) => a + b, 0) / skips.length;
  const variance = skips.reduce((a, b) => a + (b - mean) ** 2, 0) / skips.length;
  let maxRun = 1, run = 1;
  for (let i = 1; i < deltas.length; i++) {
    const sameDir = Math.sign(deltas[i]) === Math.sign(deltas[i - 1])
      && Math.abs(Math.abs(deltas[i]) - Math.abs(deltas[i - 1])) <= 2;
    if (sameDir && Math.abs(deltas[i]) > 1) { run++; if (run > maxRun) maxRun = run; }
    else run = 1;
  }
  let alt = 0;
  for (let i = 1; i < deltas.length; i++) {
    if (Math.sign(deltas[i]) !== 0 && Math.sign(deltas[i]) === -Math.sign(deltas[i - 1])
      && Math.abs(deltas[i]) > 2 && Math.abs(deltas[i - 1]) > 2) alt++;
  }
  return {
    mean, std: Math.sqrt(variance),
    unique: new Set(skips).size,
    max: Math.max(...skips),
    skips: skips.slice(0, 20),
    maxRun,
    pingPongFrac: alt / Math.max(1, deltas.length - 1),
  };
}

function setup(lines, extra) {
  vm.runInContext(`
    state.lines = ${JSON.stringify(lines)};
    state._allLines = state.lines.slice();
    state.obstructions = [];
    state.skippedRanges = [];
    state.route = null;
    state.lineStatus = {};
    state.lines.forEach(l => { state.lineStatus[l.id] = { status: 'planned', partialPct: 0, priority: 0 }; });
    state.settings.surveyType = ${JSON.stringify(extra.surveyType || '2d')};
    state.settings.progression = ${JSON.stringify(extra.progression || 'auto')};
    state.settings.optimizerMode = ${JSON.stringify(extra.optimizerMode || 'deep')};
    state.settings.optimizerIterations = ${extra.iterations ?? 1500};
    state.settings.turnRadius = ${extra.turnRadius ?? 3500};
    state.settings.runIn = ${extra.runIn ?? 7500};
    state.settings.runOut = ${extra.runOut ?? 3050};
    state.settings.startPoint = ${extra.startPoint ? JSON.stringify(extra.startPoint) : 'null'};
    state.settings.startLineIdx = ${extra.startLineIdx == null ? 'null' : extra.startLineIdx};
    state.settings.startLineId = ${extra.startLineId == null ? 'null' : extra.startLineId};
    state.settings.startLineReversed = ${extra.startLineReversed ? 'true' : 'false'};
    state.settings.startConfigured = true;
    state.settings.numSwaths = ${extra.numSwaths == null ? 'undefined' : extra.numSwaths};
    state.settings.lineDirection2d = ${JSON.stringify(extra.lineDirection2d || 'auto')};
    state._optimizerStats = null;
  `, ctx);
}

function extractOrder() {
  return vm.runInContext(`
    (function() {
      const w = state._lastRoute || [];
      const out = [];
      for (let i = 0; i < w.length; i++) {
        if (w[i].type !== 'lineStart') continue;
        const name = w[i].lineName;
        const line = state.lines.find(l => l.name === name);
        if (!line) continue;
        let end = null;
        for (let j = i + 1; j < w.length; j++) {
          if (w[j].type === 'lineEnd' && w[j].lineName === name) { end = w[j]; break; }
        }
        if (!end) continue;
        const dStart = Math.hypot(w[i].pt[0]-line.start[0], w[i].pt[1]-line.start[1]);
        const reversed = dStart > 1e-8;
        const lineIdx = state.lines.indexOf(line);
        out.push({ lineIdx, reversed, name });
      }
      return { out, stats: state._optimizerStats, nWaypoints: w.length };
    })()
  `, ctx);
}

const failures = [];
function assert(cond, msg) {
  if (!cond) failures.push(msg);
}

function run(label, extra) {
  const n = extra.n || 164;
  const lines = extra.shuffle
    ? (() => { const g = makeGrid(n); for (let i = g.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [g[i], g[j]] = [g[j], g[i]]; } return g; })()
    : makeGrid(n);
  setup(lines, extra);
  const t0 = Date.now();
  let err = null;
  try {
    vm.runInContext('state._lastRoute = computeRoute()', ctx);
  } catch (e) {
    err = e.stack || String(e);
  }
  const ms = Date.now() - t0;
  if (err) {
    console.log(JSON.stringify({ label, error: err.split('\n').slice(0, 8) }, null, 2));
    failures.push(label + ' threw: ' + String(err).split('\n')[0]);
    return;
  }
  const extracted = extractOrder();
  const orderObjs = extracted.out;
  const ranks = spatialIndex(lines, orderObjs);
  const skips = skipStats(ranks);
  const kNom = Math.max(1, Math.round((2 * (extra.turnRadius ?? 3500)) / 250));
  const summary = {
    label, ms, nVisit: orderObjs.length,
    first12ranks: ranks.slice(0, 12),
    skipMean: +skips.mean.toFixed(2),
    skipStd: +skips.std.toFixed(2),
    skipMax: skips.max,
    maxRun: skips.maxRun,
    pingPongFrac: +skips.pingPongFrac.toFixed(3),
    firstSkips: skips.skips,
    solver: extracted.stats && extracted.stats.solver,
    skipK: extracted.stats && extracted.stats.skipK,
    kNom,
  };
  console.log(JSON.stringify(summary, null, 2));

  assert(orderObjs.length === n, `${label}: visited ${orderObjs.length}/${n}`);
  if (extra.expectSolver) {
    assert(extracted.stats && extracted.stats.solver === extra.expectSolver,
      `${label}: solver ${extracted.stats && extracted.stats.solver} != ${extra.expectSolver}`);
  }
  if (extra.expectRacetrack) {
    assert(skips.maxRun >= 3, `${label}: max consistent skip run ${skips.maxRun} < 3 (ping-pong/tangle)`);
    assert(skips.pingPongFrac < 0.45, `${label}: ping-pong fraction ${skips.pingPongFrac.toFixed(2)} (2R hop zigzag)`);
    assert(skips.mean > kNom * 0.5 && skips.mean < kNom * 1.4,
      `${label}: skip mean ${skips.mean.toFixed(1)} not near k=${kNom}`);
    const first = ranks[0];
    if (extra.startLineIdx == null && extra.startLineId == null) {
      assert(first <= 2 || first >= n - 3, `${label}: started at rank ${first}, not a survey corner`);
    }
  }
  if (extra.startLineIdx != null) {
    assert(orderObjs[0].lineIdx === extra.startLineIdx,
      `${label}: first line ${orderObjs[0].lineIdx} != locked start ${extra.startLineIdx}`);
  }
  if (extra.expectSkipMax != null) {
    assert(skips.max <= extra.expectSkipMax, `${label}: skipMax ${skips.max} > ${extra.expectSkipMax}`);
  }
}

run('2d-auto-deep-164', {
  surveyType: '2d', progression: 'auto', optimizerMode: 'deep', iterations: 40, n: 164,
  expectSolver: 'racetrack', expectRacetrack: true,
});
run('2d-auto-nn-164', {
  surveyType: '2d', progression: 'auto', optimizerMode: 'nn', iterations: 1, n: 164,
  expectSolver: 'racetrack', expectRacetrack: true,
});
run('2d-auto-deep-shuffled', {
  surveyType: '2d', progression: 'auto', optimizerMode: 'deep', iterations: 40, n: 164, shuffle: true,
  expectSolver: 'racetrack', expectRacetrack: true,
});
run('2d-auto-start-line-80', {
  surveyType: '2d', progression: 'auto', optimizerMode: 'deep', iterations: 40, n: 164,
  startLineIdx: 80, startLineId: 80, expectSolver: 'racetrack', expectRacetrack: true,
});
run('3d-2swath-164', {
  surveyType: '3d', progression: 'interleaved', numSwaths: 2, n: 164, expectSkipMax: 1,
});
run('2d-low-high-164', {
  surveyType: '2d', progression: 'low-high', n: 164, expectSkipMax: 1,
});

if (failures.length) {
  console.error('\nFAILED:\n' + failures.map(f => ' - ' + f).join('\n'));
  process.exit(1);
}
console.log('\nAll route-solver assertions passed.');
process.exit(0);
