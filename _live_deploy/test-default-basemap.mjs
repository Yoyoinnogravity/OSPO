#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(dir, 'index.html'), 'utf8');
const src = fs.readFileSync(path.join(dir, 'app.js'), 'utf8');

function assert(cond, msg) {
  if (!cond) {
    console.error('FAIL:', msg);
    process.exit(1);
  }
}

assert(/app\.js\?v=17\.30/.test(html), 'app.js cache bump 17.30 missing');
assert(/const DEFAULT_BASEMAP = 'ocean'/.test(src), 'DEFAULT_BASEMAP must be ocean');
assert(/GEBCO_basemap_NCEI/.test(src), 'GEBCO NCEI tile service missing');
assert(/function createGebcoOceanLayer/.test(src), 'createGebcoOceanLayer helper missing');
assert(/function readSavedBaseLayer/.test(src), 'readSavedBaseLayer helper missing');
assert(/createGebcoOceanLayer\(\)\.addTo\(map\)/.test(src), 'Leaflet must start on GEBCO, not Esri satellite');
assert(!/initLeafletMap[\s\S]{0,800}World_Imagery/.test(src), 'initLeafletMap must not start on World Imagery');
assert(!/switchBaseMap\('satellite'\)/.test(src), 'guests/skip must not force satellite');
assert(/Skip \(use Ocean \/ GEBCO\)/.test(html), 'chooser skip must use Ocean / GEBCO');
assert(/selectBaseLayer\('ocean'\)/.test(html), 'chooser must offer Ocean / GEBCO');
assert(/value="ocean"[^>]*checked/.test(html), 'Layers radio default must be ocean');
assert(!/value="satellite"[^>]*checked/.test(html), 'Layers radio must not default to satellite');
assert(/Ocean \/ GEBCO bathymetry \(default\)/.test(html), 'Layers label must name GEBCO as default');
assert(/const DEFAULT_MAP_CENTER = \[56\.0, -96\.0\]/.test(src), 'initial view must be Canada');
assert(/function openDefaultPlanningMap/.test(src), 'login must open the 2D GEBCO map immediately');
assert(/ENC_MaritimeChartService/.test(src), 'nautical stack must include CHS Canada ENC');
assert(/UrlTemplateImageryProvider/.test(src), '3D globe must use GEBCO tiles, not only earth.jpg');
assert(/saved === 'satellite'/.test(src), 'old satellite preference must migrate to ocean');
assert(/GEBCO_NCEI_TILE_URL/.test(src), 'report renderer must use GEBCO tiles');
assert(!src.includes("img.src = `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${zoom}"),
  'report main map must not fetch Esri satellite tiles');

const store = Object.create(null);
const localStorage = {
  getItem(k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
  setItem(k, v) { store[k] = String(v); },
  removeItem(k) { delete store[k]; },
};

const ctx = {
  console,
  window: { _pendingBaseLayer: null },
  localStorage,
  L: { tileLayer() { return { addTo() { return this; }, bringToBack() {} }; } },
};
ctx.window.localStorage = localStorage;
vm.createContext(ctx);

const start = src.indexOf('const DEFAULT_BASEMAP');
const end = src.indexOf('function switchBaseMap');
assert(start >= 0 && end > start, 'could not slice basemap helpers from app.js');
vm.runInContext(src.slice(start, end), ctx, { filename: 'app.js#basemap' });

assert(vm.runInContext('DEFAULT_BASEMAP', ctx) === 'ocean', 'runtime DEFAULT_BASEMAP is ocean');
assert(vm.runInContext('readSavedBaseLayer()', ctx) === 'ocean', 'empty storage defaults to ocean');
assert(store.candooka_baseLayer === 'ocean', 'empty storage writes ocean');

store.candooka_baseLayer = 'satellite';
delete store.candooka_baseLayer_v;
delete store.candooka_baseLayer_chosen;
assert(vm.runInContext('readSavedBaseLayer()', ctx) === 'ocean', 'legacy satellite default migrates to ocean');
assert(store.candooka_baseLayer === 'ocean', 'migrated storage is ocean');

store.candooka_baseLayer = 'nautical';
store.candooka_baseLayer_v = '1';
assert(vm.runInContext('readSavedBaseLayer()', ctx) === 'nautical', 'explicit non-satellite choice is kept');

console.log(JSON.stringify({
  ok: true,
  defaultBasemap: 'ocean',
  provider: 'GEBCO NCEI',
  cache: '17.30',
}, null, 2));
process.exit(0);
