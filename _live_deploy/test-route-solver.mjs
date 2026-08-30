#!/usr/bin/env node
/**
 * Auto ships a skip-k racetrack from a survey corner (k ≈ 2R/spacing).
 * 3D finishes each swath as a block — never 0, n/2, 1, n/2+1 zigzag.
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

assert(/app\.js\?v=17\.19/.test(html), 'app.js cache bump 17.19 missing');
assert(/id="val-turn-radius">3\.5km/.test(html), 'toolbar RADIUS default must be 3.5km not 5.1');
assert(/id="input-turn-radius" value="3500"/.test(html), 'turn-radius input default must be 3500 m');
assert(!/value="5100"/.test(html), 'HTML must not default min turn radius to 5100');
assert(src.includes("createPane('routePane')"), 'planned route must have its own map pane');
assert(src.includes('function _fitMapToPlannedRoute'), 'after a plan the map must fit to the vessel route');
assert(src.includes('function dubinsMinRadiusFallback'), 'heading-change must not fall back to a straight chord');
assert(src.includes('colour clock starts at first acquisition'), 'time colour must start at first lineStart t=0');
assert(src.includes(".addTo(layerRoute)"), 'Start/End markers must sit on the route layer');
assert(!src.includes('else if (!surveyVisible)'), 'Show All must still paint on-line vessel track');
assert(src.includes('Load a preplot first, then click Route Planning'), 'empty Plan Route must toast, not silent-return');
assert(src.includes('if (showStartLineChooser()) return'), 'chooser miss must still executePlanRoute');
assert(html.includes('1500 sequences, keep the fastest'), 'chooser Auto must score 1500 then keep the fastest');
assert(html.includes('skip-k racetrack'), 'chooser Auto must describe skip-k racetrack');
assert(!html.includes('fastest of 1500 options'), 'chooser must not advertise 1500-option TSP');
assert(html.includes('simple nearest neighbour'), 'auto-nn must stay real NN');
assert(src.includes('showLabels: false'), 'labels must default off');
assert(src.includes('lmSetPriority'), 'Line Manager priority setter missing');
assert(src.includes('Math.max(1, Math.min(100, priorityNum))'), 'Line Manager 1-100 clamp missing');
assert(src.includes('function _prioNorm'), 'priority normalizer missing');
assert(src.includes('first !== lo && first !== hi'), 'corner-start guard missing');
assert(src.includes('swath-blocks'), '3D block-complete stats missing');
assert(!src.includes('fillBudget:'), 'Family E every-rank fill must be gone');
assert(!src.includes('Mixed-radix'), 'mixed-radix line-level DP must stay gone');
assert(!html.toLowerCase().includes('users-db.json'), 'index.html must not touch users-db');
assert(!/fetch\([^)]*users-db\.json/.test(src), 'app.js must not fetch users-db.json');

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

function visitNames() {
  return vm.runInContext(`
    (function() {
      const w = state._lastRoute || [];
      const names = [];
      const seen = new Set();
      for (const x of w) {
        if (x.type === 'lineStart' && x.lineName && !seen.has(x.lineName)) {
          seen.add(x.lineName);
          names.push(x.lineName);
        }
      }
      return names;
    })()
  `, ctx);
}

function ranksFromNames(names) {
  return names.map((nm) => parseInt(nm.slice(1), 10) - 1000);
}

function skipStats(ranks) {
  const skips = [];
  let flips = 0;
  let prevDir = 0;
  for (let i = 1; i < ranks.length; i++) {
    const d = ranks[i] - ranks[i - 1];
    skips.push(Math.abs(d));
    const dir = Math.sign(d);
    if (dir && prevDir && dir !== prevDir) flips++;
    if (dir) prevDir = dir;
  }
  const mean = skips.reduce((a, b) => a + b, 0) / skips.length;
  const sorted = skips.slice().sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)];
  const hist = {};
  for (const s of skips) hist[s] = (hist[s] || 0) + 1;
  const mode = Number(Object.entries(hist).sort((a, b) => b[1] - a[1])[0][0]);
  const modeFrac = hist[mode] / skips.length;
  const std = Math.sqrt(skips.reduce((a, b) => a + (b - mean) * (b - mean), 0) / skips.length);
  return {
    first: ranks[0],
    last: ranks[ranks.length - 1],
    mean,
    median,
    mode,
    modeFrac,
    std,
    max: Math.max(...skips),
    pingPong: flips / (ranks.length - 1),
    hops: skips.length,
  };
}

function plan(lines, extra) {
  setup(lines, extra);
  const t0 = Date.now();
  vm.runInContext('state._lastRoute = computeRoute()', ctx);
  const names = visitNames();
  const ranks = ranksFromNames(names);
  return {
    ms: Date.now() - t0,
    nVisit: names.length,
    ranks,
    skip: skipStats(ranks),
    stats: vm.runInContext('state._optimizerStats', ctx),
  };
}

const grid12 = makeGrid(12);
const nn = plan(grid12, { optimizerMode: 'nn', iterations: 1 });
assert(nn.nVisit === 12, 'NN must visit all 12, got ' + nn.nVisit);
assert(nn.stats && nn.stats.mode === 'nn', 'NN mode not recorded');

const auto12 = plan(grid12, { optimizerMode: 'deep', iterations: 40 });
assert(auto12.nVisit === 12, 'Auto 12-line must visit all 12, got ' + auto12.nVisit);
assert(auto12.stats.mode === 'racetrack', 'Auto mode should be racetrack, got ' + auto12.stats.mode);
assert(auto12.skip.first === 0 || auto12.skip.first === 11,
  '12-line Auto must start at a spatial corner, first=' + auto12.skip.first);

const R = 3500, spacing = 250;
const kNom = Math.max(1, Math.round((2 * R) / spacing));
assert(kNom === 28, 'expected kNom 28 for R=3500 spacing=250, got ' + kNom);

const grid164 = makeGrid(164);
const t2d = plan(grid164, { surveyType: '2d', progression: 'auto', optimizerMode: 'deep' });
assert(t2d.nVisit === 164, '2D Auto must visit all 164, got ' + t2d.nVisit);
assert(t2d.stats.mode === 'racetrack', '2D mode should be racetrack, got ' + t2d.stats.mode);
assert(t2d.skip.first === 0 || t2d.skip.first === 163,
  '2D Auto must start at a spatial corner, first=' + t2d.skip.first);
assert(Math.abs(t2d.skip.mode - kNom) <= 8,
  `2D skip mode ${t2d.skip.mode} not near k=${kNom} (mean ${t2d.skip.mean.toFixed(2)} includes wrap hops)`);
assert(t2d.skip.modeFrac > 0.55,
  `2D only ${(t2d.skip.modeFrac * 100).toFixed(1)}% of hops are skip-${t2d.skip.mode}; racetrack should dominate`);
assert(t2d.skip.pingPong < 0.35,
  `2D ping-pong ${t2d.skip.pingPong.toFixed(3)} looks like a tangled tour`);
assert(t2d.stats.constructor === 'racetrack',
  '2D must ship racetrack, got ' + t2d.stats.constructor);
assert(t2d.stats.optionsEvaluated >= 1000,
  '2D Auto must score toward 1500 sequences, got ' + t2d.stats.optionsEvaluated);
assert(t2d.stats.optionsEvaluated <= 1500,
  '2D Auto must stop at 1500, got ' + t2d.stats.optionsEvaluated);

const t3d = plan(grid164, { surveyType: '3d', progression: 'interleaved', numSwaths: 2 });
assert(t3d.nVisit === 164, '3D must visit all 164, got ' + t3d.nVisit);
assert(t3d.stats && t3d.stats.mode === 'swath-blocks',
  '3D mode should be swath-blocks, got ' + (t3d.stats && t3d.stats.mode));
const zig = t3d.ranks[0] === 0 && t3d.ranks[1] === 82 && t3d.ranks[2] === 1 && t3d.ranks[3] === 83;
assert(!zig, '3D must not zigzag 0,82,1,83 (line-level swath interleave)');
const first82 = t3d.ranks.slice(0, 82);
const swathLo = first82.every((r) => r < 82);
const swathHi = first82.every((r) => r >= 82);
assert(swathLo || swathHi,
  '3D must finish one swath before the other, first8=' + first82.slice(0, 8).join(','));
assert(!(t3d.ranks[0] === 0 && t3d.ranks[1] === 1 && t3d.ranks[2] === 2),
  '3D must not crawl adjacent 0,1,2 inside a swath (same-heading sail-back)');
const inSwath = skipStats(first82);
assert(Math.abs(inSwath.mode - kNom) <= 8,
  `3D within-swath skip mode ${inSwath.mode} not near k=${kNom}`);
assert(inSwath.modeFrac > 0.55,
  `3D within-swath only ${(inSwath.modeFrac * 100).toFixed(1)}% skip-${inSwath.mode}; racetrack should dominate`);
assert(t3d.stats.optionsEvaluated >= 1000,
  '3D Auto must score toward 1500 sequences, got ' + t3d.stats.optionsEvaluated);
assert(t3d.stats.optionsEvaluated <= 1500,
  '3D Auto must stop at 1500, got ' + t3d.stats.optionsEvaluated);

const headings = vm.runInContext(`
  (function() {
    const w = state._lastRoute || [];
    const lines = state.lines;
    const out = [];
    const seen = new Set();
    for (const x of w) {
      if (x.type !== 'lineStart' || !x.lineName || seen.has(x.lineName)) continue;
      seen.add(x.lineName);
      const L = lines.find(l => l.name === x.lineName);
      if (!L || !x.pt) continue;
      const dS = Math.hypot(x.pt[0] - L.start[0], x.pt[1] - L.start[1]);
      const dE = Math.hypot(x.pt[0] - L.end[0], x.pt[1] - L.end[1]);
      out.push(dE < dS);
    }
    return out;
  })()
`, ctx);
let sameHead = 0;
for (let i = 1; i < Math.min(headings.length, 82); i++) {
  if (headings[i] === headings[i - 1]) sameHead++;
}
assert(sameHead / 81 < 0.25,
  '3D first swath headings must alternate (racetrack), same-heading hops=' + sameHead);

const nameS1 = 'L' + (1000 + t3d.ranks[0]);
const nameLast = 'L' + (1000 + t3d.ranks[t3d.ranks.length - 1]);
const col = vm.runInContext(`
  (function() {
    const v = _routeVisitOrder(state._lastRoute);
    const a = visitColorForLine(${JSON.stringify(nameS1)}, v);
    const z = visitColorForLine(${JSON.stringify(nameLast)}, v);
    const t0 = v.t0ByName && v.t0ByName.get(${JSON.stringify(nameS1)});
    const tZ = v.t0ByName && v.t0ByName.get(${JSON.stringify(nameLast)});
    return { a, z, t0, tZ, total: v.totalSec };
  })()
`, ctx);
assert(col.total > 0 && col.t0 === 0, 'first line must sit at t=0, t0=' + col.t0);
assert(col.tZ > col.t0, 'last line must be later in time than the first');
assert(col.a === 'rgb(255,69,58)', 'first line in time must be red, got ' + col.a);
assert(col.z !== col.a, 'last line in time must not match the start colour');

const turnGeom = vm.runInContext(`
  (function() {
    state.settings.turnRadius = 3500;
    const r = getEffectiveTurnRadius();
    const lat0 = -20.5, lon0 = 110.2;
    const mLat = 111320;
    const mLon = 111320 * Math.cos(lat0 * Math.PI / 180);
    const L0s = [lat0, lon0];
    const L0e = [lat0, lon0 + 20000 / mLon];
    const L1e = [lat0 + 6670 / mLat, lon0 + 20000 / mLon];
    const brng = bearing(L0s, L0e);
    const ro = destinationPoint(L0e, brng, 7500);
    const ri = destinationPoint(L1e, (brng + 180) % 360, 7500);
    const wps = [
      { type: 'lineEnd', pt: L0e, lineName: 'A' },
      { type: 'runOutEnd', pt: ro, lineName: 'A' },
      { type: 'runInStart', pt: ri, lineName: 'B' },
      { type: 'lineStart', pt: L1e, lineName: 'B' },
    ];
    const arc = computeArcTurn(wps, 1);
    return { n: arc.length, R: r };
  })()
`, ctx);
assert(turnGeom.R === 3500, 'min R must stay at user 3500 m, got ' + turnGeom.R);
assert(turnGeom.n > 4, 'line-change must be a Dubins curve, not a 2-pt chord, n=' + turnGeom.n);

const liveLike = makeGrid(164, 667, 44500);
const tLive = plan(liveLike, { surveyType: '3d', progression: 'interleaved', numSwaths: 2, turnRadius: 3500 });
assert(tLive.nVisit === 164, '667m 3D must visit all 164');
const liveFirst = tLive.ranks.slice(0, 82);
assert(liveFirst.every((r) => r < 82) || liveFirst.every((r) => r >= 82),
  '667m 3D must stay in one swath for the first 82 visits');
assert(!(tLive.ranks[0] === 0 && tLive.ranks[1] === 1),
  '667m 3D must not adjacent-crawl (k ≈ 2R/667 ≈ 10)');

// Line Manager 1-100: high-priority lines acquired first, still a racetrack within the bucket.
vm.runInContext(`
  state.lineStatus[0].priority = 1;
  state.lineStatus[1].priority = 1;
  state.lineStatus[2].priority = 100;
`, ctx);
const tPrio = plan(makeGrid(12), { surveyType: '2d', progression: 'auto' });
assert(tPrio.nVisit === 12, 'priority Auto must visit all 12');
assert(src.includes('min="1" max="100"'), 'Line Manager UI 1-100 missing');

console.log(JSON.stringify({
  ok: true,
  cache: '17.19',
  rule: 'skip-k racetrack from a corner; 3D skip-k racetrack per swath',
  kNom,
  nn: { visit: nn.nVisit, mode: nn.stats.mode, ms: nn.ms },
  auto12: { first: auto12.skip.first, mean: +auto12.skip.mean.toFixed(2), mode: auto12.stats.mode },
  t2d: {
    first: t2d.skip.first,
    mode: t2d.skip.mode,
    modeFrac: +t2d.skip.modeFrac.toFixed(3),
    mean: +t2d.skip.mean.toFixed(2),
    median: t2d.skip.median,
    std: +t2d.skip.std.toFixed(2),
    pingPong: +t2d.skip.pingPong.toFixed(3),
    k: t2d.stats.skipK,
    constructor: t2d.stats.constructor,
    options: t2d.stats.optionsEvaluated,
    ms: t2d.ms,
    h: t2d.stats.finalSec != null ? +(t2d.stats.finalSec / 3600).toFixed(2) : null,
  },
  t3d: {
    first8: t3d.ranks.slice(0, 8),
    inSwathMode: inSwath.mode,
    inSwathModeFrac: +inSwath.modeFrac.toFixed(3),
    sameHeadHops: sameHead,
    mode: t3d.stats.mode,
    skipK: t3d.stats.skipK,
    options: t3d.stats.optionsEvaluated,
    ms: t3d.ms,
  },
  tLive667: {
    first8: tLive.ranks.slice(0, 8),
    mode: tLive.stats && tLive.stats.mode,
    skipK: tLive.stats && tLive.stats.skipK,
    ms: tLive.ms,
  },
}, null, 2));
process.exit(0);
