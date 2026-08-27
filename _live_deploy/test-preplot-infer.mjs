#!/usr/bin/env node
/**
 * Node checks: P1 auto-loads (16.81); named/clear CSV auto-loads;
 * ambiguous delimited files get a QGIS-simple sample + X field / Y field dialog.
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
  CSV_COLUMN_SAMPLE_ROWS,
  buildDelimitedTextDialogHtml,
  delimitedTextFieldLabel,
} = ctx;

assert(typeof parsePreplotBestEffort === 'function', 'parsePreplotBestEffort missing');

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
assert(resultIsAutoLoad(named) === true, 'named CSV headers must auto-map, conf=' + named.confidence);

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
assert(clear.lines && clear.lines.length >= 1, 'whitespace numeric with UTM pair should parse');
assert(layoutHasKnownXY(clear.layout) !== true, 'unlabeled columns are not already-known X/Y');
assert(resultIsAutoLoad(clear) === true, 'clear unlabeled UTM should auto-map (16.81), conf=' + clear.confidence);

const unlabeledAmbiguous = [
  '1001 512345.6 6210000.0 412345.6 5310000.0',
  '1002 512355.6 6210100.0 412355.6 5310100.0',
  '1003 512365.6 6210200.0 412365.6 5310200.0',
  '1004 512375.6 6210300.0 412375.6 5310300.0',
  '1005 512385.6 6210400.0 412385.6 5310500.0',
  '1006 512395.6 6210500.0 412395.6 5310500.0',
].join('\n');
const ambLayout = inferDelimitedLayout(unlabeledAmbiguous.split('\n'));
assert(ambLayout, 'ambiguous file must still infer a layout');
assert(ambLayout.headers.length >= 4, 'sample must expose multiple real columns, got ' + ambLayout.headers.length);
const amb = parsePreplotBestEffort(unlabeledAmbiguous, 31, 'N');
const table = preparePreplotMapperTable(unlabeledAmbiguous, amb.layout || ambLayout);
assert(table.headerCols.length >= 4, 'picker must show >=4 columns, got ' + table.headerCols.length);
assert(!table.headerCols.some(h => /^H0100/i.test(String(h))), 'picker must not repeat H0100 in headers');
assert((table.sampleRows[0] || []).length >= 4, 'sample row must have multiple fields');
assert(resultIsAutoLoad(amb) === false, 'ambiguous unlabeled must ask (QGIS dialog). conf=' + amb.confidence);

const manyRows = Array.from({ length: 14 }, (_, i) =>
  `L1,${1001 + i},${512345.6 + i},${6210000.0 + i * 10}`
).join('\n');
const manyTable = preparePreplotMapperTable(manyRows, inferDelimitedLayout(manyRows.split('\n')));
assert(CSV_COLUMN_SAMPLE_ROWS === 10, 'sample size constant must be 10, got ' + CSV_COLUMN_SAMPLE_ROWS);
assert(manyTable.sampleRows.length === 10, 'picker must show first ~10 data rows, got ' + manyTable.sampleRows.length);
assert(manyTable.sampleRows[0][0] === 'L1', 'sample cells must be real parsed values, got ' + JSON.stringify(manyTable.sampleRows[0]));

assert(!src.includes('CONFIRM COLUMNS'), 'old CONFIRM COLUMNS title must be gone');
assert(!src.includes('This is X') && !src.includes('This is Y'), 'click-wizard This is X/Y must be gone');
assert(!src.includes('csv-coord-type'), 'coordinate-type extra step must be gone');
assert(!src.includes('csv-col-line'), 'Line Name dropdown must be gone');
assert(typeof buildDelimitedTextDialogHtml === 'function', 'QGIS dialog builder missing');
assert(delimitedTextFieldLabel('easting', 0) === 'easting', 'named columns keep their names');
assert(delimitedTextFieldLabel('Column 3', 2) === 'field_3', 'unlabeled columns use QGIS field_N');
const dlgHtml = buildDelimitedTextDialogHtml(
  ['line', 'sp', 'easting', 'northing'],
  [['A', '1', '512345.6', '6210000.0'], ['A', '2', '512445.6', '6210100.0']],
  { colX: 2, colY: 3 }
);
assert(dlgHtml.includes('Delimited Text'), 'dialog title must be Delimited Text');
assert(dlgHtml.includes('X field') && dlgHtml.includes('Y field'), 'QGIS X field and Y field labels required');
assert(dlgHtml.includes('>Import</button>'), 'Import button required');
assert(dlgHtml.includes('Cancel'), 'Cancel button required');
assert(dlgHtml.includes('easting') && dlgHtml.includes('northing'), 'dropdowns use column names from the sample');
assert(/<option value="2" selected>easting<\/option>/.test(dlgHtml), 'X field must pre-select easting');
assert(/<option value="3" selected>northing<\/option>/.test(dlgHtml), 'Y field must pre-select northing');
assert(dlgHtml.includes('512345.6') && dlgHtml.includes('6210000.0'), 'sample table shows first data rows');
assert(!dlgHtml.includes('Click a sample'), 'no click-column wizard copy');
assert(!dlgHtml.includes('Line Name'), 'no Line Name extra step');
assert(!dlgHtml.includes('Shotpoint'), 'no SP extra step');

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

console.log(JSON.stringify({
  ok: true,
  p1: { lines: p1Parsed.lines.length, conf: p1Parsed.confidence, format: p1Parsed.format, skipColumnMap: !!p1Parsed.skipColumnMap },
  namedCsv: { lines: named.lines.length, conf: named.confidence, knownXY: layoutHasKnownXY(named.layout) },
  unlabeledClear: { lines: clear.lines.length, conf: clear.confidence, auto: resultIsAutoLoad(clear) },
  unlabeledAmbiguous: { conf: amb.confidence, cols: table.headerCols.length, auto: resultIsAutoLoad(amb) },
  sampleRows: manyTable.sampleRows.length,
}, null, 2));
process.exit(0);
