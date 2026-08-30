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
assert(overview.weight <= 1.3, 'overview line-changes must be thin, got weight ' + overview.weight);
assert(String(overview.color).toLowerCase() !== '#ff9500', 'overview must not use screaming orange #ff9500');
assert(focus.weight >= 2.2, 'selected leg must be heavier than overview');
assert(focus.color !== overview.color, 'selected leg colour must differ from overview');
assert(ctx._routeSegFocused(0, null) === false, 'no highlight means nothing focused');
assert(ctx._routeSegFocused(3, { startWpIdx: 2, endWpIdx: 5 }) === true, 'segment inside highlight');
assert(ctx._routeSegFocused(5, { startWpIdx: 2, endWpIdx: 5 }) === false, 'end index is exclusive');
assert(ctx._routeSegFocused(1, { startWpIdx: 2, endWpIdx: 5 }) === false, 'before highlight');

assert(!src.includes("color: '#ff9500', weight: 2.5, opacity: 0.85"),
  'old heavy orange transit stroke must be gone');
assert(src.includes("_routeTransitOverviewStyle"), 'overview style helper missing');
assert(src.includes("mode: 'overview'"), 'plan/show-all must request overview drawing');
assert(src.includes("mode: 'step'"), 'stepper must request step drawing');
assert(!/const subset = state\.route\.slice/.test(src),
  'stepper must not slice the route (that hid context and still scribbled on Show All)');
assert(html.includes('id="route-step-all-btn"'), 'Show All button needs an id');
assert(/app\.js\?v=17\.00/.test(html), 'app.js cache bump missing');
assert(/style\.min\.css\?v=3\.32/.test(html), 'css cache bump missing');

console.log(JSON.stringify({
  ok: true,
  overviewWeight: overview.weight,
  overviewColor: overview.color,
  focusWeight: focus.weight,
  focusColor: focus.color,
}, null, 2));
process.exit(0);
