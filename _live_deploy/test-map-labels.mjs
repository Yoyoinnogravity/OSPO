#!/usr/bin/env node
/**
 * Map/line labels start OFF on first visit and on each preplot file load.
 * Visible LABELS OFF / ON tabs live under the preplot summary.
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

function elStub(id) {
  const el = {
    id,
    style: {},
    value: '',
    textContent: '',
    innerHTML: '',
    checked: false,
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
    _s: { candooka_show_labels: '1' },
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

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const { setMapLabelsVisible, resetMapLabelsForNewPreplot, toggleLabels, beginPreplotLoad, finishPreplotLoad } = ctx;

function showLabels() {
  return vm.runInContext('state.showLabels', ctx);
}

assert(typeof setMapLabelsVisible === 'function', 'setMapLabelsVisible missing');
assert(typeof resetMapLabelsForNewPreplot === 'function', 'resetMapLabelsForNewPreplot missing');
assert(showLabels() === false, 'first visit / leftover candooka_show_labels=1 must still start OFF, got ' + showLabels());

setMapLabelsVisible(true, { skipRender: true });
assert(showLabels() === true, 'LABELS ON must set showLabels');
assert(window.localStorage.getItem('candooka_show_labels') === '1', 'toggle writes candooka_show_labels');

resetMapLabelsForNewPreplot();
assert(showLabels() === false, 'new preplot load must force labels OFF');
assert(window.localStorage.getItem('candooka_show_labels') === '0', 'load reset writes labels off');

toggleLabels();
assert(showLabels() === true, 'A-button toggleLabels must turn labels on');
resetMapLabelsForNewPreplot();
assert(showLabels() === false, 'second file load must turn labels off again');

assert(typeof beginPreplotLoad === 'function', 'beginPreplotLoad missing');
assert(typeof finishPreplotLoad === 'function', 'finishPreplotLoad missing');
assert(/resetMapLabelsForNewPreplot/.test(src), 'file-load path must call resetMapLabelsForNewPreplot');
assert(src.includes("LABELS OFF"), 'OFF tab label missing');
assert(src.includes("LABELS ON"), 'ON tab label missing');
assert(src.includes('labels-tab-off') && src.includes('labels-tab-on'), 'OFF/ON tab ids missing');
assert(!src.includes('Line numbers & SP labels are shown by default'), 'old default-ON toast must be gone');
assert(/showLabels:\s*false/.test(src), 'state.showLabels default must be false');

assert(/id="layer-toggle-labels"[^>]*onchange/.test(html), 'Layers menu still has labels checkbox');
assert(!/id="layer-toggle-labels"\s+checked/.test(html), 'Layers menu labels checkbox must not start checked');
assert(html.includes('LABELS OFF / ON under the preplot summary') || html.includes('toggleLabels()'), 'map A button still present');
assert(/app\.js\?v=17\.17/.test(html), 'app.js cache bump missing');

const els = {};
const kids = [];
document.getElementById = (id) => els[id] || null;
document.createElement = (tag) => {
  const el = elStub(tag);
  Object.defineProperty(el, 'id', {
    configurable: true,
    get() { return this._id || ''; },
    set(v) { this._id = v; if (v) els[v] = this; },
  });
  return el;
};
const stack = elStub('survey-summary-stack');
stack.appendChild = (child) => { kids.push(child); if (child.id) els[child.id] = child; return child; };

const overlay = ctx._ensureMapDisplayToggle(stack);
assert(overlay, 'map-display overlay must be created under the preplot summary');
assert(overlay.innerHTML.includes('LABELS OFF'), 'overlay must show LABELS OFF');
assert(overlay.innerHTML.includes('LABELS ON'), 'overlay must show LABELS ON');
assert(/id="labels-tab-off"[^>]*\bactive/.test(overlay.innerHTML), 'OFF tab must be active after load');
assert(!/id="labels-tab-on"[^>]*\bactive/.test(overlay.innerHTML), 'ON tab must not be active after load');
assert(overlay.innerHTML.includes('MAP LABELS'), 'overlay title MAP LABELS missing');
assert(overlay.innerHTML.includes('3D SWATHS'), 'overlay must show 3D SWATHS');
assert(overlay.innerHTML.includes('SWATHS OFF') && overlay.innerHTML.includes('SWATHS ON'), 'overlay must show SWATHS OFF/ON tabs');
assert(overlay.innerHTML.includes('Number of swaths'), 'overlay must show number of swaths control');
assert(overlay.innerHTML.includes('id="map-num-swaths"'), 'overlay must have map-num-swaths input');
assert(/id="layer-toggle-swaths"[^>]*onchange/.test(html), 'Layers menu 3D Swaths checkbox missing');
assert(/style\.min\.css\?v=3\.33/.test(html), 'style.min.css cache bump 3.33 missing');
assert(kids.length >= 1, 'overlay must be appended under the summary stack');

console.log(JSON.stringify({
  ok: true,
  defaultOff: true,
  leftoverLocalStorageIgnored: true,
  toggleOnThenLoadResets: true,
  tabs: ['LABELS OFF', 'LABELS ON'],
}, null, 2));
process.exit(0);
