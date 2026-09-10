#!/usr/bin/env node
/**
 * Node checks: P1 auto-loads; CSV with known X/Y headers auto-loads;
 * anything else is skipped with a short format hint (no column wizard).
 * Loads app.js with a tiny DOM stub.
 */
import fs from 'fs';
import vm from 'vm';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appPath = path.resolve(__dirname, 'app.js');
const src = fs.readFileSync(appPath, 'utf8');

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
    getItem(k) { return this._s[k] || null; },
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

const {
  parsePreplotBestEffort,
  detectFormat,
  looksLikeUkuaaP1,
  inferDelimitedLayout,
  preparePreplotMapperTable,
  resultIsAutoLoad,
  dataRowsForPreplotMapping,
  layoutHasKnownXY,
  PREPLOT_FORMAT_HINT,
  skipUnsupportedPreplot,
} = ctx;

assert(typeof parsePreplotBestEffort === 'function', 'parsePreplotBestEffort missing');
assert(typeof skipUnsupportedPreplot === 'function', 'skipUnsupportedPreplot missing');
assert(typeof PREPLOT_FORMAT_HINT === 'string' && PREPLOT_FORMAT_HINT.length > 10, 'PREPLOT_FORMAT_HINT missing');
assert(/P1/.test(PREPLOT_FORMAT_HINT), 'skip message must mention P1');
assert(/X and Y/i.test(PREPLOT_FORMAT_HINT), 'skip message must mention X and Y');
assert(/easting\/northing/i.test(PREPLOT_FORMAT_HINT), 'skip message must mention easting/northing');

function vRec(line, sp, latDeg, lonDeg, e, n) {
  const lat = String(Math.round(latDeg)).padStart(2, '0') + '0000.00N';
  const lon = String(Math.round(lonDeg)).padStart(3, '0') + '0000.00E';
  const ln = String(line).padEnd(12, ' ').slice(0, 12);
  const spS = String(sp).padStart(6, ' ');
  return 'S' + ln + '   ' + spS + lat + lon + ' ' + e.toFixed(1).padStart(8, ' ') + ' ' + n.toFixed(1).padStart(9, ' ');
}

const p1 = [
  'H0100 Survey Area                     KK',
  'H0200 Shotpoint Location              Shot',
  'H0802 Geodetic Datum                  WGS84 UTM Zone 31N',
  vRec('LINE001', 1001, 56, 3, 512345.6, 6210000.0),
  vRec('LINE001', 1101, 56, 3, 512345.6, 6213700.0),
  vRec('LINE002', 1001, 56, 3, 514345.6, 6210000.0),
  vRec('LINE002', 1101, 56, 3, 514345.6, 6213700.0),
].join('\n');

const p1Rows = p1.split('\n');
assert(looksLikeUkuaaP1(p1Rows) === true, 'H0100 snippet must look like UKOOA P1');
assert(detectFormat(p1Rows) === 'p190', 'H0100 snippet must detect as p190, not csv');

const p1Parsed = parsePreplotBestEffort(p1, 31, 'N');
assert(p1Parsed.format === 'p190' || p1Parsed.skipColumnMap, 'P1 result format ' + p1Parsed.format + ' reason=' + p1Parsed.reason);
assert(p1Parsed.lines && p1Parsed.lines.length >= 1, 'P1 must load lines, got ' + (p1Parsed.lines && p1Parsed.lines.length) + ' conf=' + p1Parsed.confidence + ' reason=' + p1Parsed.reason);
assert(resultIsAutoLoad(p1Parsed) === true, 'P1 must auto-load, no confirm dialog. conf=' + p1Parsed.confidence);
assert(p1Parsed.skipColumnMap === true, 'P1 must never CSV-map (skipColumnMap)');

const namedCsv = [
  'line,sp,easting,northing',
  'A,1,512345.6,6210000.0',
  'A,2,512445.6,6210100.0',
  'B,1,513345.6,6210000.0',
  'B,2,513445.6,6210100.0',
  'C,1,514345.6,6210000.0',
  'C,2,514445.6,6210100.0',
].join('\n');
const named = parsePreplotBestEffort(namedCsv, 31, 'N');
assert(named.lines && named.lines.length >= 2, 'named CSV must produce lines, got ' + (named.lines && named.lines.length) + ' conf=' + named.confidence);
assert(layoutHasKnownXY(named.layout) === true, 'easting/northing headers mean X/Y are already known');
assert(resultIsAutoLoad(named) === true, 'named CSV headers must auto-map, conf=' + named.confidence + ' layout=' + JSON.stringify(named.layout && { colX: named.layout.colX, colY: named.layout.colY, conf: named.layout.confidence }));

const xyCsv = [
  'line,x,y',
  'A,512345.6,6210000.0',
  'A,512445.6,6210100.0',
  'B,513345.6,6210000.0',
  'B,513445.6,6210100.0',
].join('\n');
const xy = parsePreplotBestEffort(xyCsv, 31, 'N');
assert(layoutHasKnownXY(xy.layout) === true, 'x/y headers must be recognized');
assert(resultIsAutoLoad(xy) === true, 'x/y CSV must auto-load, conf=' + xy.confidence);

const llCsv = [
  'line,lon,lat',
  'A,3.1,56.2',
  'A,3.2,56.3',
  'B,3.3,56.2',
  'B,3.4,56.3',
].join('\n');
const ll = parsePreplotBestEffort(llCsv, 31, 'N');
assert(layoutHasKnownXY(ll.layout) === true, 'lon/lat headers must be recognized');
assert(resultIsAutoLoad(ll) === true, 'lon/lat CSV must auto-load, conf=' + ll.confidence + ' lines=' + (ll.lines && ll.lines.length));

const unlabeledClear = [
  'L1 1001 512345.6 6210000.0',
  'L1 1002 512355.6 6210100.0',
  'L1 1003 512365.6 6210200.0',
  'L2 1001 514345.6 6210000.0',
  'L2 1002 514355.6 6210100.0',
  'L2 1003 514365.6 6210200.0',
].join('\n');
const clear = parsePreplotBestEffort(unlabeledClear, 31, 'N');
assert(layoutHasKnownXY(clear.layout) !== true, 'unlabeled columns are not already-known X/Y');
assert(resultIsAutoLoad(clear) === false, 'unlabeled CSV must skip, not auto-load or ask. conf=' + clear.confidence);

const unlabeledAmbiguous = [
  '1001 512345.6 6210000.0 412345.6 5310000.0',
  '1002 512355.6 6210100.0 412355.6 5310100.0',
  '1003 512365.6 6210200.0 412365.6 5310200.0',
  '1004 512375.6 6210300.0 412375.6 5310300.0',
  '1005 512385.6 6210400.0 412385.6 5310400.0',
  '1006 512395.6 6210500.0 412395.6 5310500.0',
].join('\n');
const amb = parsePreplotBestEffort(unlabeledAmbiguous, 31, 'N');
assert(resultIsAutoLoad(amb) === false, 'ambiguous unlabeled must skip (not auto, not wizard). conf=' + amb.confidence);

assert(!src.includes('CONFIRM COLUMNS'), 'old CONFIRM COLUMNS title must be gone');
assert(!src.includes('This is X') && !src.includes('This is Y'), 'click-wizard This is X/Y must be gone');
assert(!src.includes('csv-column-mapper'), 'csv-column-mapper dialog must be gone');
assert(!src.includes('_showColumnMapperDialog'), 'column mapper dialog function must be gone');
assert(!src.includes('buildDelimitedTextDialogHtml'), 'QGIS/sample dialog builder must be gone');
assert(!src.includes('csv-coord-type'), 'coordinate-type extra step must be gone');
assert(!src.includes('csv-col-line'), 'Line Name dropdown must be gone');
assert(!src.includes('X field'), 'QGIS X field dropdown must be gone');
assert(!src.includes('Choose X and Y coordinates'), 'sample picker title must be gone');
assert(src.includes('PREPLOT_FORMAT_HINT'), 'skip-message constant must exist');

const hOnlyTrap = [
  'H0100 Survey Area, KK',
  'H0200 Shotpoint Location, Shot',
  'H0802 Geodetic Datum, WGS84 UTM 31N',
  vRec('LINE001', 1001, 56, 3, 512345.6, 6210000.0),
  vRec('LINE001', 1101, 56, 3, 512345.6, 6213700.0),
].join('\n');
const trapFmt = detectFormat(hOnlyTrap.split('\n'));
assert(trapFmt === 'p190', 'H-records with commas must still be P1, got ' + trapFmt);
const trap = parsePreplotBestEffort(hOnlyTrap, 31, 'N');
assert(resultIsAutoLoad(trap) === true, 'comma-in-H P1 must auto-load as P1, not CSV. conf=' + trap.confidence + ' fmt=' + trap.format);
assert(dataRowsForPreplotMapping(hOnlyTrap.split('\n')).every(r => !/^H\d{4}/.test(r.trim())), 'mapping rows skip H-records');

const p1Table = preparePreplotMapperTable(p1, null);
assert(p1Table && p1Table.headerCols, 'P1 internal field table still builds');
assert(!p1Table.headerCols.some(h => /^H0100/i.test(String(h))), 'P1 must not expose H0100 as a CSV column');

console.log(JSON.stringify({
  ok: true,
  skipMessage: PREPLOT_FORMAT_HINT,
  p1: { lines: p1Parsed.lines.length, conf: p1Parsed.confidence, format: p1Parsed.format, skipColumnMap: !!p1Parsed.skipColumnMap, auto: resultIsAutoLoad(p1Parsed) },
  namedCsv: { lines: named.lines.length, conf: named.confidence, knownXY: layoutHasKnownXY(named.layout), auto: resultIsAutoLoad(named) },
  xyCsv: { lines: xy.lines && xy.lines.length, auto: resultIsAutoLoad(xy) },
  lonLatCsv: { lines: ll.lines && ll.lines.length, auto: resultIsAutoLoad(ll) },
  unlabeledClear: { conf: clear.confidence, auto: resultIsAutoLoad(clear) },
  unlabeledAmbiguous: { conf: amb.confidence, auto: resultIsAutoLoad(amb) },
}, null, 2));
process.exit(0);
