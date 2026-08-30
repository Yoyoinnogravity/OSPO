#!/usr/bin/env node
/**
 * Auto scores up to N shooting sequences (default 1500), then stops.
 * The client gets the minimum-time plan only. Not ILS iteration count.
 */
import fs from 'fs';
import vm from 'vm';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(path.resolve(__dirname, 'app.js'), 'utf8');
const html = fs.readFileSync(path.resolve(__dirname, 'index.html'), 'utf8');

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

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
  setTimeout: () => 0, clearTimeout() {}, setInterval: () => 0, clearInterval() {},
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

assert(/app\.js\?v=17\.01/.test(html), 'app.js cache bump 17.01 missing');
assert(html.includes('fastest of 1500 options'), 'chooser Auto is not fastest-of-1500');
assert(html.includes('simple nearest neighbour'), 'auto-nn must stay real NN');
assert(src.includes('showLabels: false'), 'labels must default off');
assert(src.includes('optionsEvaluated >= targetOptions'), 'hard option cap missing');
assert(!src.includes('for (let iter = 0; iter <'), 'ILS iteration loop must not run');
assert(src.includes('then STOP. Not ILS iterations'), 'stop-at-N comment missing');
assert(!html.toLowerCase().includes('users-db.json'), 'index.html must not touch users-db');

function makeGrid(n, spacingM = 250, lengthM = 20000, east0 = 0) {
  const lat0 = -20.5, lon0 = 110.2;
  const mLat = 111320;
  const mLon = 111320 * Math.cos(lat0 * Math.PI / 180);
  const lines = [];
  for (let i = 0; i < n; i++) {
    const dlon = (east0 + i * spacingM) / mLon;
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
    state.settings.startPoint = null;
    state.settings.startLineIdx = ${extra.startLineIdx == null ? 'null' : extra.startLineIdx};
    state.settings.startLineId = ${extra.startLineId == null ? 'null' : extra.startLineId};
    state.settings.startLineReversed = false;
    state.settings.startConfigured = true;
    state.settings.numSwaths = ${extra.numSwaths == null ? 2 : extra.numSwaths};
    state.settings.lineDirection2d = 'auto';
    state._optimizerStats = null;
  `, ctx);
}

function visitCount() {
  return vm.runInContext(`
    (function() {
      const w = state._lastRoute || [];
      const seen = new Set();
      for (const x of w) {
        if (x.type === 'lineStart' && x.lineName) seen.add(x.lineName);
      }
      return seen.size;
    })()
  `, ctx);
}

function plan(lines, extra) {
  setup(lines, extra);
  const t0 = Date.now();
  vm.runInContext('state._lastRoute = computeRoute()', ctx);
  return {
    ms: Date.now() - t0,
    nVisit: visitCount(),
    stats: vm.runInContext('state._optimizerStats', ctx),
  };
}

const grid12 = makeGrid(12);
const nn = plan(grid12, { optimizerMode: 'nn', iterations: 1 });
assert(nn.nVisit === 12, 'NN must visit all 12, got ' + nn.nVisit);
assert(nn.stats && nn.stats.mode === 'nn', 'NN mode not recorded');

const capped = plan(grid12, { optimizerMode: 'deep', iterations: 40 });
assert(capped.nVisit === 12, 'capped Auto must visit all 12, got ' + capped.nVisit);
assert(capped.stats.optionsEvaluated <= 40, 'must stop at 40 options, scored ' + capped.stats.optionsEvaluated);
assert(capped.stats.optionsEvaluated >= 1, 'must score at least one option');
assert(capped.stats.finalSec != null, 'Auto must report finalSec');
assert(capped.stats.finalSec <= nn.stats.finalSec + 0.5,
  `Auto ${capped.stats.finalSec.toFixed(1)}s slower than NN ${nn.stats.finalSec.toFixed(1)}s`);

const grid24 = makeGrid(24);
const deep = plan(grid24, { optimizerMode: 'deep', iterations: 1500 });
assert(deep.nVisit === 24, 'Auto 24-line must visit all 24, got ' + deep.nVisit);
assert(deep.stats.optionsEvaluated <= 1500, 'must not exceed 1500, scored ' + deep.stats.optionsEvaluated);
assert(deep.stats.optionsEvaluated === 1500,
  '24-line family must fill the 1500 budget, scored ' + deep.stats.optionsEvaluated);
assert(deep.stats.mode === 'fastest-of-n', 'mode should be fastest-of-n, got ' + deep.stats.mode);
assert(!deep.stats.capped, '1500 options should finish before the time cap');
if (deep.stats.candidateSec) {
  const vals = Object.values(deep.stats.candidateSec).filter(v => typeof v === 'number' && isFinite(v));
  if (vals.length) {
    assert(deep.stats.finalSec <= Math.min(...vals) + 0.5,
      'shipped plan slower than a recorded candidate');
  }
}

const t3d = plan(makeGrid(24), { surveyType: '3d', progression: 'interleaved', numSwaths: 2, iterations: 1500 });
assert(t3d.nVisit === 24, '3D interleave must visit all 24, got ' + t3d.nVisit);
assert((t3d.stats.optionsEvaluated || 0) <= 1500, '3D must stop at 1500 options');

console.log(JSON.stringify({
  ok: true,
  cache: '17.01',
  rule: 'score N shooting sequences (default 1500), ship the fastest, stop',
  cap40: { options: capped.stats.optionsEvaluated, ms: capped.ms, h: +(capped.stats.finalSec / 3600).toFixed(2) },
  grid24: {
    options: deep.stats.optionsEvaluated,
    constructor: deep.stats.constructor,
    candidates: deep.stats.candidateSec,
    ms: deep.ms,
    h: +(deep.stats.finalSec / 3600).toFixed(2),
  },
  t3d: { visit: t3d.nVisit, options: t3d.stats.optionsEvaluated, ms: t3d.ms },
}, null, 2));
process.exit(0);
