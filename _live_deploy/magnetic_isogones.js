// ===== MAGNETIC DECLINATION ISOGONES =====
// Curves of equal magnetic declination (variation) from WMM, drawn on the map.
// Requires wmm_declination.js (WMMDeclination.declination).

var _magIsoState = {
 enabled: false,
 intervalDeg: 1,
 moveHandler: null,
 clickHandler: null,
 redrawTimer: null
};

function magIsoFmtDecl(d) {
 if (!isFinite(d)) return '--';
 const abs = Math.abs(d);
 const hemi = d >= 0 ? 'E' : 'W';
 return abs.toFixed(1) + '\u00b0' + hemi;
}

function magIsoGetInterval() {
 const el = document.getElementById('mag-iso-interval');
 const v = el ? parseFloat(el.value) : _magIsoState.intervalDeg;
 return (isFinite(v) && v > 0) ? v : 1;
}

function magIsoEnsureLayer() {
 if (!map) return null;
 if (!mapLayers.declination) {
  mapLayers.declination = L.layerGroup();
 }
 return mapLayers.declination;
}

function magIsoClear() {
 const layer = mapLayers && mapLayers.declination;
 if (layer) layer.clearLayers();
}

/** Marching-squares isolines for a regular lat/lon grid of values. */
function magIsoContours(grid, lats, lons, levels) {
 const rows = lats.length;
 const cols = lons.length;
 const segmentsByLevel = levels.map(() => []);

 function interp(a, b, va, vb, level) {
  if (Math.abs(vb - va) < 1e-12) return 0.5;
  return (level - va) / (vb - va);
 }

 for (let li = 0; li < levels.length; li++) {
  const level = levels[li];
  const segs = segmentsByLevel[li];
  for (let r = 0; r < rows - 1; r++) {
   for (let c = 0; c < cols - 1; c++) {
    const v00 = grid[r][c], v10 = grid[r][c + 1];
    const v01 = grid[r + 1][c], v11 = grid[r + 1][c + 1];
    if (![v00, v10, v01, v11].every(isFinite)) continue;

    // Binary index: corners above level
    let idx = 0;
    if (v00 >= level) idx |= 1;
    if (v10 >= level) idx |= 2;
    if (v11 >= level) idx |= 4;
    if (v01 >= level) idx |= 8;
    if (idx === 0 || idx === 15) continue;

    const lat0 = lats[r], lat1 = lats[r + 1];
    const lon0 = lons[c], lon1 = lons[c + 1];
    const bottom = [lat0, lon0 + (lon1 - lon0) * interp(lon0, lon1, v00, v10, level)];
    const right = [lat0 + (lat1 - lat0) * interp(lat0, lat1, v10, v11, level), lon1];
    const top = [lat1, lon0 + (lon1 - lon0) * interp(lon0, lon1, v01, v11, level)];
    const left = [lat0 + (lat1 - lat0) * interp(lat0, lat1, v00, v01, level), lon0];

    // Edge midpoints keyed by side: 0 bottom, 1 right, 2 top, 3 left
    const edge = [bottom, right, top, left];
    // Classic marching-squares edge pairs
    const cases = {
     1: [[3, 0]], 2: [[0, 1]], 3: [[3, 1]], 4: [[1, 2]],
     5: [[3, 2], [0, 1]], // saddle - pick average-based split
     6: [[0, 2]], 7: [[3, 2]], 8: [[2, 3]], 9: [[0, 2]],
     10: [[0, 3], [1, 2]], 11: [[1, 2]], 12: [[1, 3]],
     13: [[0, 1]], 14: [[0, 3]]
    };
    let pairs = cases[idx];
    if (!pairs) continue;
    // Ambiguous saddles: choose connectivity by average
    if (idx === 5 || idx === 10) {
     const avg = (v00 + v10 + v01 + v11) / 4;
     if (idx === 5) {
      pairs = avg >= level ? [[3, 2], [0, 1]] : [[3, 0], [1, 2]];
     } else {
      pairs = avg >= level ? [[0, 3], [1, 2]] : [[0, 1], [2, 3]];
     }
    }
    pairs.forEach(([a, b]) => {
     segs.push([edge[a], edge[b]]);
    });
   }
  }
 }
 return segmentsByLevel;
}

/** Stitch short segments into polylines. */
function magIsoStitch(segments) {
 if (!segments.length) return [];
 const tol = 1e-7;
 const used = new Array(segments.length).fill(false);
 const lines = [];

 function near(a, b) {
  return Math.abs(a[0] - b[0]) < tol && Math.abs(a[1] - b[1]) < tol;
 }

 for (let i = 0; i < segments.length; i++) {
  if (used[i]) continue;
  used[i] = true;
  const poly = [segments[i][0], segments[i][1]];
  let grew = true;
  while (grew) {
   grew = false;
   for (let j = 0; j < segments.length; j++) {
    if (used[j]) continue;
    const [a, b] = segments[j];
    const head = poly[0], tail = poly[poly.length - 1];
    if (near(tail, a)) { poly.push(b); used[j] = true; grew = true; }
    else if (near(tail, b)) { poly.push(a); used[j] = true; grew = true; }
    else if (near(head, b)) { poly.unshift(a); used[j] = true; grew = true; }
    else if (near(head, a)) { poly.unshift(b); used[j] = true; grew = true; }
   }
  }
  if (poly.length >= 2) lines.push(poly);
 }
 return lines;
}

function magIsoPickLevels(minV, maxV, interval) {
 const levels = [];
 if (!(maxV >= minV) || !(interval > 0)) return levels;
 const start = Math.ceil((minV - 1e-9) / interval) * interval;
 for (let v = start; v <= maxV + 1e-9; v += interval) {
  // Avoid flooding with near-zero duplicates from float
  const r = Math.round(v / interval) * interval;
  if (Math.abs(r) < interval * 0.01) levels.push(0);
  else levels.push(Number(r.toFixed(6)));
 }
 // Unique
 return [...new Set(levels)];
}

function magIsoColor(level) {
 // East (positive) warm amber; west (negative) cool cyan; agonic white
 if (Math.abs(level) < 1e-6) return '#f8fafc';
 if (level > 0) return '#f59e0b';
 return '#38bdf8';
}

function magIsoRebuild() {
 if (!_magIsoState.enabled || !map) return;
 if (typeof WMMDeclination === 'undefined' || typeof WMMDeclination.declination !== 'function') {
  showToast('Magnetic model not loaded');
  return;
 }

 const layer = magIsoEnsureLayer();
 if (!layer) return;
 layer.clearLayers();

 const bounds = map.getBounds().pad(0.08);
 const south = bounds.getSouth();
 const north = bounds.getNorth();
 const west = bounds.getWest();
 const east = bounds.getEast();
 const spanLat = Math.max(0.01, north - south);
 const spanLon = Math.max(0.01, east - west);

 // Adaptive grid: denser when zoomed in, capped for performance
 const zoom = map.getZoom();
 const targetCells = zoom >= 8 ? 48 : zoom >= 5 ? 36 : 28;
 const nLat = Math.max(12, Math.min(60, Math.round(targetCells * (spanLat / Math.max(spanLat, spanLon)))));
 const nLon = Math.max(12, Math.min(60, Math.round(targetCells * (spanLon / Math.max(spanLat, spanLon)))));

 const lats = [];
 const lons = [];
 for (let i = 0; i <= nLat; i++) lats.push(south + (spanLat * i) / nLat);
 for (let j = 0; j <= nLon; j++) lons.push(west + (spanLon * j) / nLon);

 const date = new Date();
 const grid = [];
 let minV = Infinity, maxV = -Infinity;
 for (let i = 0; i < lats.length; i++) {
  const row = [];
  for (let j = 0; j < lons.length; j++) {
   let d;
   try {
    d = WMMDeclination.declination(lats[i], lons[j], date);
   } catch (_) {
    d = NaN;
   }
   row.push(d);
   if (isFinite(d)) {
    if (d < minV) minV = d;
    if (d > maxV) maxV = d;
   }
  }
  grid.push(row);
 }

 if (!isFinite(minV) || !isFinite(maxV)) {
  showToast('Could not compute declination for this view');
  return;
 }

 const interval = magIsoGetInterval();
 _magIsoState.intervalDeg = interval;
 let levels = magIsoPickLevels(minV, maxV, interval);
 // Always include agonic line (0) when it crosses the range
 if (minV < 0 && maxV > 0 && !levels.includes(0)) levels.push(0);
 levels.sort((a, b) => a - b);

 const segsPerLevel = magIsoContours(grid, lats, lons, levels);
 segsPerLevel.forEach((segs, li) => {
  const level = levels[li];
  const color = magIsoColor(level);
  const weight = Math.abs(level) < 1e-6 ? 2.2 : 1.4;
  const lines = magIsoStitch(segs);
  lines.forEach(latlngs => {
   if (latlngs.length < 2) return;
   L.polyline(latlngs, {
    color,
    weight,
    opacity: 0.9,
    interactive: false,
    className: 'mag-isogone'
   }).addTo(layer);

   // Label near midpoint of longest-ish stretch
   const mid = latlngs[Math.floor(latlngs.length / 2)];
   L.marker(mid, {
    interactive: false,
    icon: L.divIcon({
     className: 'mag-iso-label',
     html: `<span style="color:${color};font-size:10px;font-weight:700;text-shadow:0 0 3px #000,0 1px 2px #000;white-space:nowrap;">${magIsoFmtDecl(level)}</span>`,
     iconSize: [48, 14],
     iconAnchor: [24, 7]
    })
   }).addTo(layer);
  });
 });

 if (!map.hasLayer(layer)) layer.addTo(map);

 const hint = document.getElementById('mag-iso-status');
 if (hint) {
  hint.textContent = `WMM · ${magIsoFmtDecl(minV)} to ${magIsoFmtDecl(maxV)} · every ${interval}\u00b0 · ${date.getFullYear()}`;
 }
}

function magIsoScheduleRebuild() {
 if (!_magIsoState.enabled) return;
 if (_magIsoState.redrawTimer) clearTimeout(_magIsoState.redrawTimer);
 _magIsoState.redrawTimer = setTimeout(() => {
  _magIsoState.redrawTimer = null;
  magIsoRebuild();
 }, 280);
}

function magIsoOnClick(e) {
 if (!_magIsoState.enabled || typeof WMMDeclination === 'undefined') return;
 try {
  const d = WMMDeclination.declination(e.latlng.lat, e.latlng.lng, new Date());
  const f = typeof WMMDeclination.field === 'function'
   ? WMMDeclination.field(e.latlng.lat, e.latlng.lng, new Date())
   : null;
  const tip = f && isFinite(f.incl)
   ? `Declination ${magIsoFmtDecl(d)} · Inclination ${f.incl.toFixed(1)}\u00b0`
   : `Declination ${magIsoFmtDecl(d)}`;
  showToast(tip, 4500);
 } catch (_) {}
}

function magIsoEnable() {
 if (!map) {
  showToast('Overlays need the 2D map - switch to 2D first');
  return;
 }
 if (typeof WMMDeclination === 'undefined') {
  showToast('Magnetic model failed to load');
  return;
 }
 _magIsoState.enabled = true;
 magIsoEnsureLayer();
 magIsoRebuild();
 if (!_magIsoState.moveHandler) {
  _magIsoState.moveHandler = () => magIsoScheduleRebuild();
  map.on('moveend', _magIsoState.moveHandler);
  map.on('zoomend', _magIsoState.moveHandler);
 }
 if (!_magIsoState.clickHandler) {
  _magIsoState.clickHandler = magIsoOnClick;
  map.on('click', _magIsoState.clickHandler);
 }
 showToast('Magnetic declination isogones on - click map for local value', 4500);
}

function magIsoDisable() {
 _magIsoState.enabled = false;
 if (_magIsoState.redrawTimer) {
  clearTimeout(_magIsoState.redrawTimer);
  _magIsoState.redrawTimer = null;
 }
 if (map && _magIsoState.moveHandler) {
  map.off('moveend', _magIsoState.moveHandler);
  map.off('zoomend', _magIsoState.moveHandler);
 }
 if (map && _magIsoState.clickHandler) {
  map.off('click', _magIsoState.clickHandler);
 }
 _magIsoState.moveHandler = null;
 _magIsoState.clickHandler = null;
 magIsoClear();
 if (mapLayers.declination && map && map.hasLayer(mapLayers.declination)) {
  map.removeLayer(mapLayers.declination);
 }
 mapLayers.declination = null;
 const hint = document.getElementById('mag-iso-status');
 if (hint) hint.textContent = '';
}

function magIsoToggle(force) {
 const on = (typeof force === 'boolean') ? force : !_magIsoState.enabled;
 const cb = document.getElementById('layer-overlay-declination');
 if (cb) cb.checked = on;
 if (on) magIsoEnable(); else magIsoDisable();
}

function magIsoIntervalChanged() {
 if (_magIsoState.enabled) magIsoScheduleRebuild();
}
