// ===== GLOBAL BATHYMETRY CONTOURS =====
// Isolines generated in the client from a worldwide ETOPO 1-arc-minute grid
// (NOAA via /api/bathy-grid.php). Not Europe-only EMODnet vectors.
var _bathyIsoState = {
 enabled: false,
 interval: 'auto',
 moveHandler: null,
 clickHandler: null,
 redrawTimer: null,
 inFlight: null
};

function bathyIsoFmtDepth(elev) {
 if (!isFinite(elev)) return '--';
 if (elev >= 0) return elev.toFixed(0) + ' m elev';
 return Math.abs(elev).toFixed(0) + ' m';
}

function bathyIsoGetInterval(minV, maxV, zoom) {
 const el = document.getElementById('bathy-iso-interval');
 const raw = el ? el.value : _bathyIsoState.interval;
 if (raw && raw !== 'auto') {
  const v = parseFloat(raw);
  if (isFinite(v) && v > 0) return v;
 }
 const oceanMin = minV; // most negative
 const oceanMax = Math.min(0, maxV);
 const span = Math.abs(oceanMax - oceanMin);
 if (zoom >= 10) return span > 250 ? 50 : 20;
 if (zoom >= 8) return span > 600 ? 100 : 50;
 if (zoom >= 6) return span > 1500 ? 200 : 100;
 if (zoom >= 4) return span > 3000 ? 500 : 200;
 return span > 4000 ? 1000 : 500;
}

function bathyIsoEnsureLayer() {
 if (!map) return null;
 if (!mapLayers.bathyIso) mapLayers.bathyIso = L.layerGroup();
 return mapLayers.bathyIso;
}

function bathyIsoClear() {
 const layer = mapLayers && mapLayers.bathyIso;
 if (layer) layer.clearLayers();
}

function bathyIsoColor(level) {
 // level is elevation (negative = depth). Shallow cyan → deep navy. Coast white.
 if (Math.abs(level) < 0.5) return '#f8fafc';
 const d = Math.abs(level);
 if (d < 50) return '#7dd3fc';
 if (d < 200) return '#38bdf8';
 if (d < 1000) return '#0ea5e9';
 if (d < 3000) return '#0369a1';
 return '#0c4a6e';
}

function bathyIsoPickLevels(minV, maxV, interval) {
 const levels = [];
 if (!(interval > 0) || !(maxV >= minV)) return levels;
 const oceanMin = minV;
 const oceanMax = Math.min(0, maxV);
 if (!(oceanMax >= oceanMin)) return levels;
 // Work in depth-positive space, emit elevation (negative) levels
 const deep = Math.abs(oceanMin);
 const shallow = Math.abs(oceanMax);
 const start = Math.ceil((shallow + 1e-6) / interval) * interval;
 for (let d = start; d <= deep + 1e-6; d += interval) {
  const r = Math.round(d / interval) * interval;
  levels.push(-Number(r.toFixed(4)));
 }
 if (minV < 0 && maxV >= 0) levels.push(0);
 return [...new Set(levels)].sort((a, b) => a - b);
}

function bathyIsoContours(grid, lats, lons, levels) {
 const rows = lats.length, cols = lons.length;
 const segmentsByLevel = levels.map(() => []);
 function interp(va, vb, level) {
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
    let idx = 0;
    if (v00 >= level) idx |= 1;
    if (v10 >= level) idx |= 2;
    if (v11 >= level) idx |= 4;
    if (v01 >= level) idx |= 8;
    if (idx === 0 || idx === 15) continue;
    const lat0 = lats[r], lat1 = lats[r + 1];
    const lon0 = lons[c], lon1 = lons[c + 1];
    const bottom = [lat0, lon0 + (lon1 - lon0) * interp(v00, v10, level)];
    const right = [lat0 + (lat1 - lat0) * interp(v10, v11, level), lon1];
    const top = [lat1, lon0 + (lon1 - lon0) * interp(v01, v11, level)];
    const left = [lat0 + (lat1 - lat0) * interp(v00, v01, level), lon0];
    const edge = [bottom, right, top, left];
    let pairs = {
     1: [[3, 0]], 2: [[0, 1]], 3: [[3, 1]], 4: [[1, 2]],
     5: [[3, 2], [0, 1]], 6: [[0, 2]], 7: [[3, 2]], 8: [[2, 3]],
     9: [[0, 2]], 10: [[0, 3], [1, 2]], 11: [[1, 2]], 12: [[1, 3]],
     13: [[0, 1]], 14: [[0, 3]]
    }[idx];
    if (!pairs) continue;
    if (idx === 5 || idx === 10) {
     const avg = (v00 + v10 + v01 + v11) / 4;
     if (idx === 5) pairs = avg >= level ? [[3, 2], [0, 1]] : [[3, 0], [1, 2]];
     else pairs = avg >= level ? [[0, 3], [1, 2]] : [[0, 1], [2, 3]];
    }
    pairs.forEach(([a, b]) => segs.push([edge[a], edge[b]]));
   }
  }
 }
 return segmentsByLevel;
}

function bathyIsoStitch(segments) {
 if (!segments.length) return [];
 const tol = 1e-7;
 const used = new Array(segments.length).fill(false);
 const lines = [];
 const near = (a, b) => Math.abs(a[0] - b[0]) < tol && Math.abs(a[1] - b[1]) < tol;
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

function bathyIsoSetStatus(text) {
 const hint = document.getElementById('bathy-iso-status');
 if (hint) hint.textContent = text || '';
}

function bathyIsoRebuild() {
 if (!_bathyIsoState.enabled || !map) return;
 const bounds = map.getBounds().pad(0.04);
 const south = bounds.getSouth();
 const north = bounds.getNorth();
 const west = bounds.getWest();
 const east = bounds.getEast();
 const url = `/api/bathy-grid.php?south=${south.toFixed(4)}&west=${west.toFixed(4)}&north=${north.toFixed(4)}&east=${east.toFixed(4)}&nx=72&ny=72`;
 const token = {};
 _bathyIsoState.inFlight = token;
 bathyIsoSetStatus('Sampling global bathymetry…');
 fetch(url).then(r => r.json()).then(data => {
  if (_bathyIsoState.inFlight !== token || !_bathyIsoState.enabled) return;
  if (!data || data.error || !data.z) {
   bathyIsoSetStatus(data && data.error ? data.error : 'Grid failed');
   showToast(data && data.error ? data.error : 'Bathymetry grid failed');
   return;
  }
  const lats = data.lats, lons = data.lons, grid = data.z;
  let minV = Infinity, maxV = -Infinity;
  for (let i = 0; i < grid.length; i++) {
   for (let j = 0; j < grid[i].length; j++) {
    const v = grid[i][j];
    if (typeof v === 'number' && isFinite(v)) {
     if (v < minV) minV = v;
     if (v > maxV) maxV = v;
    }
   }
  }
  if (!isFinite(minV) || minV >= 0) {
   bathyIsoClear();
   bathyIsoSetStatus('No seafloor in this view (land)');
   return;
  }
  const zoom = map.getZoom();
  const interval = bathyIsoGetInterval(minV, maxV, zoom);
  const levels = bathyIsoPickLevels(minV, maxV, interval);
  const layer = bathyIsoEnsureLayer();
  if (!layer) return;
  layer.clearLayers();
  const segsPerLevel = bathyIsoContours(grid, lats, lons, levels);
  segsPerLevel.forEach((segs, li) => {
   const level = levels[li];
   const color = bathyIsoColor(level);
   const weight = Math.abs(level) < 0.5 ? 2.2 : 1.35;
   const lines = bathyIsoStitch(segs);
   lines.forEach(latlngs => {
    if (latlngs.length < 2) return;
    L.polyline(latlngs, {
     color, weight, opacity: 0.92, interactive: false, className: 'bathy-isobath'
    }).addTo(layer);
    const mid = latlngs[Math.floor(latlngs.length / 2)];
    const label = Math.abs(level) < 0.5 ? '0 m' : Math.abs(level).toFixed(0) + ' m';
    L.marker(mid, {
     interactive: false,
     icon: L.divIcon({
      className: 'bathy-iso-label',
      html: `<span style="color:${color};font-size:10px;font-weight:700;text-shadow:0 0 3px #000,0 1px 2px #000;white-space:nowrap;">${label}</span>`,
      iconSize: [48, 14],
      iconAnchor: [24, 7]
     })
    }).addTo(layer);
   });
  });
  if (!map.hasLayer(layer)) layer.addTo(map);
  const deep = Math.abs(minV).toFixed(0);
  const shallow = Math.abs(Math.min(0, maxV)).toFixed(0);
  bathyIsoSetStatus(`ETOPO 1′ · ${shallow}–${deep} m · every ${interval} m`);
 }).catch(() => {
  if (_bathyIsoState.inFlight !== token) return;
  bathyIsoSetStatus('Bathymetry request failed');
  showToast('Bathymetry request failed');
 });
}

function bathyIsoScheduleRebuild() {
 if (!_bathyIsoState.enabled) return;
 if (_bathyIsoState.redrawTimer) clearTimeout(_bathyIsoState.redrawTimer);
 _bathyIsoState.redrawTimer = setTimeout(() => {
  _bathyIsoState.redrawTimer = null;
  bathyIsoRebuild();
 }, 320);
}

function bathyIsoOnClick(e) {
 if (!_bathyIsoState.enabled) return;
 fetch(`/api/get-depth.php?lat=${e.latlng.lat.toFixed(5)}&lon=${e.latlng.lng.toFixed(5)}`)
  .then(r => r.json())
  .then(data => {
   if (!data || data.elevation === undefined) return;
   showToast(bathyIsoFmtDepth(data.elevation), 4500);
  }).catch(() => {});
}

function bathyIsoEnable() {
 if (!map) {
  showToast('Overlays need the 2D map - switch to 2D first');
  return;
 }
 _bathyIsoState.enabled = true;
 bathyIsoEnsureLayer();
 bathyIsoRebuild();
 if (!_bathyIsoState.moveHandler) {
  _bathyIsoState.moveHandler = () => bathyIsoScheduleRebuild();
  map.on('moveend', _bathyIsoState.moveHandler);
  map.on('zoomend', _bathyIsoState.moveHandler);
 }
 if (!_bathyIsoState.clickHandler) {
  _bathyIsoState.clickHandler = bathyIsoOnClick;
  map.on('click', _bathyIsoState.clickHandler);
 }
 showToast('Global bathymetry contours on — generated from ETOPO (worldwide)', 4500);
}

function bathyIsoDisable() {
 _bathyIsoState.enabled = false;
 _bathyIsoState.inFlight = null;
 if (_bathyIsoState.redrawTimer) {
  clearTimeout(_bathyIsoState.redrawTimer);
  _bathyIsoState.redrawTimer = null;
 }
 if (map && _bathyIsoState.moveHandler) {
  map.off('moveend', _bathyIsoState.moveHandler);
  map.off('zoomend', _bathyIsoState.moveHandler);
 }
 if (map && _bathyIsoState.clickHandler) {
  map.off('click', _bathyIsoState.clickHandler);
 }
 _bathyIsoState.moveHandler = null;
 _bathyIsoState.clickHandler = null;
 bathyIsoClear();
 if (mapLayers.bathyIso && map && map.hasLayer(mapLayers.bathyIso)) {
  map.removeLayer(mapLayers.bathyIso);
 }
 mapLayers.bathyIso = null;
 bathyIsoSetStatus('');
}

function bathyIsoToggle(force) {
 const on = (typeof force === 'boolean') ? force : !_bathyIsoState.enabled;
 const cb = document.getElementById('layer-overlay-bathy');
 if (cb) cb.checked = on;
 if (on) bathyIsoEnable(); else bathyIsoDisable();
}

function bathyIsoIntervalChanged() {
 if (_bathyIsoState.enabled) bathyIsoScheduleRebuild();
}
