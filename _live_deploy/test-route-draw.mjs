#!/usr/bin/env node
/**
 * Planned route drawing: Show All must not paint every line-change as a
 * heavy orange scribble. Overview is thin/muted; Prev/Next focuses one leg.
 */
import fs from 'fs';
import vm from 'vm';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appPath = path.resolve(__dirname, 'app.js');
const htmlPath = path.resolve(__dirname, 'index.html');
const src = fs.readFileSync(appPath, 'utf8');
const html = fs.readFileSync(htmlPath, 'utf8');
const css = fs.readFileSync(path.resolve(__dirname, 'style.css'), 'utf8');

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function elStub(id) {
  const el = {
    id,
    style: {},
    value: '',
    textContent: '',
    innerHTML: '',
    classList: { add() {}, remove() {}, contains() { return false; }, toggle() {} },
    addEventListener() {},
    removeEventListener() {},
    appendChild() { return arguments[0]; },
    remove() {},
    querySelector() { return elStub('q'); },
    querySelectorAll() { return []; },
    getBoundingClientRect() { return { top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 }; },
    focus() {},
    select() {},
    click() {},
    setAttribute() {},
    getAttribute() { return null; },
    children: [],
    parentNode: { removeChild() {} },
  };
  return el;
}

const document = {
  readyState: 'loading',
  body: { appendChild() {}, removeChild() {}, style: {} },
  documentElement: { style: {} },
  addEventListener() {},
  removeEventListener() {},
  createElement: (tag) => elStub(tag),
  getElementById: (id) => elStub(id),
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
  onerror: null,
  localStorage: {
    _s: {},
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
  },
};

const ctx = {
  window, document,
  console,
  setTimeout, clearTimeout, setInterval, clearInterval,
  localStorage: window.localStorage,
  fetch: async () => ({ json: async () => ({}), ok: true }),
  alert() {},
  L: { DomEvent: { disableScrollPropagation() {}, disableClickPropagation() {} } },
  MutationObserver: class { observe() {} disconnect() {} },
  Node: function () {},
  HTMLElement: function () {},
  navigator: { userAgent: 'node' },
  location: { href: 'http://localhost/' },
  URL, Blob: class {},
  FileReader: class {},
  atob, btoa,
};
ctx.global = ctx;
ctx.self = ctx;
ctx.window = window;
window.window = window;
window.document = document;
ctx.globalThis = ctx;

vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'app.js' });

const overview = ctx._routeTransitOverviewStyle();
const focus = ctx._routeTransitFocusStyle();

assert(overview, 'overview transit style missing');
assert(focus, 'focus transit style missing');
assert(overview.weight >= 2.2, 'overview line-changes must be visible, got weight ' + overview.weight);
assert(String(overview.color).toLowerCase() !== '#ff9500', 'overview must not use screaming orange #ff9500');
assert(focus.weight >= 2.2, 'selected leg must stay visible');
assert(ctx._routeSegFocused(0, null) === false, 'no highlight means nothing focused');
assert(ctx._routeSegFocused(3, { startWpIdx: 2, endWpIdx: 5 }) === true, 'segment inside highlight');
assert(ctx._routeSegFocused(5, { startWpIdx: 2, endWpIdx: 5 }) === false, 'end index is exclusive');
assert(ctx._routeSegFocused(1, { startWpIdx: 2, endWpIdx: 5 }) === false, 'before highlight');

assert(!src.includes("color: '#ff9500', weight: 2.5, opacity: 0.85"),
  'old heavy orange transit stroke must be gone');
assert(!src.includes("color: '#ffcc33', weight: 2, opacity: 0.85"),
  'unfocused run-out must keep time colour, not flat yellow');
assert(src.includes("_routeTransitOverviewStyle"), 'overview style helper missing');
assert(src.includes('function visitColorAtIdx'), 'transits must take survey-time colour');
assert(src.includes('_routeTransitOverviewStyle(tColor)'), 'overview transits must be passed time colour');
assert(src.includes('function _buildRouteTimelineSegments'), 'timeline segment builder missing');
assert(src.includes('data-timeline-seg'), 'timeline bar must paint per-segment colours');
assert(src.includes('Time-line colour is BINDING'), 'time-line colour lock comment missing');
assert(src.includes('function _fitMapToPlannedRoute'), 'plan must fit the map to the vessel route');
assert(src.includes("mode: 'overview'"), 'plan/show-all must request overview drawing');
assert(src.includes("mode: 'step'"), 'stepper must request step drawing');
assert(!/const subset = state\.route\.slice/.test(src),
  'stepper must not slice the route (that hid context and still scribbled on Show All)');
assert(html.includes('id="route-step-all-btn"'), 'Show All button needs an id');
assert(/app\.js\?v=17\.40/.test(html), 'app.js cache bump missing');
assert(/style\.min\.css\?v=3\.34/.test(html), 'css cache bump missing');
assert(html.includes('id="btn-plan-route"'), 'ROUTE PLANNING needs an id');
assert(html.includes('btn-plan-route'), 'ROUTE PLANNING must use the prominent plan-route class');
assert(css.includes('.btn-plan-route') && css.includes('background: #30d158'),
  'ROUTE PLANNING must be a filled green primary action');

const timed = ctx._routeTransitOverviewStyle('rgb(255,69,58)');
assert(timed.color === 'rgb(255,69,58)', 'overview style must accept time colour, got ' + timed.color);

const tlDemo = vm.runInContext(`
  (function() {
    state.settings = state.settings || {};
    state.settings.speed = 4.5;
    state.settings.turnSpeed = 6;
    const wps = [
      { type: 'lineStart', pt: [0, 0], lineName: 'A' },
      { type: 'lineEnd', pt: [0.2, 0], lineName: 'A' },
      { type: 'runOutEnd', pt: [0.22, 0], lineName: 'A' },
      { type: 'runInStart', pt: [0.22, 0.02], lineName: 'B' },
      { type: 'lineStart', pt: [0.2, 0.02], lineName: 'B' },
      { type: 'lineEnd', pt: [0, 0.02], lineName: 'B' }
    ];
    const segs = _buildRouteTimelineSegments(wps);
    const html = _routeTimelineTrackHtml(segs);
    const v = _routeVisitOrder(wps);
    return {
      n: segs.length,
      types: segs.map(s => s.type),
      first: segs.find(s => s.type === 'line').color,
      last: segs.filter(s => s.type === 'line').pop().color,
      html: html,
      t0: v.t0ByName.get('A'),
      red: visitColorAtIdx(v, 0, 'A')
    };
  })()
`, ctx);
assert(tlDemo.types.includes('line') && tlDemo.types.includes('transit'),
  'timeline must include line and transit segments, types=' + tlDemo.types);
assert(tlDemo.first === 'rgb(255,69,58)', 'timeline first line must be red, got ' + tlDemo.first);
assert(tlDemo.last !== tlDemo.first, 'timeline last line must not be the start colour');
assert(tlDemo.html.includes('data-timeline-seg="line"'), 'timeline HTML missing line segs');
assert(tlDemo.red === 'rgb(255,69,58)', 'visitColorAtIdx first line must be red, got ' + tlDemo.red);
assert(tlDemo.t0 === 0, 'colour clock must start at first line, t0=' + tlDemo.t0);

console.log(JSON.stringify({
  ok: true,
  overviewWeight: overview.weight,
  overviewColor: overview.color,
  timedColor: timed.color,
  focusWeight: focus.weight,
  focusColor: focus.color,
  timelineFirst: tlDemo.first,
  timelineLast: tlDemo.last,
}, null, 2));
process.exit(0);
