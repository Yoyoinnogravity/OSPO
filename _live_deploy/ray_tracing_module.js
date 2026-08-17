// ===== ACOUSTIC RAY TRACING (OBN / water-column) =====
// Velocity Mode: constant | gradient | layered | mackenzie
// Layered 1D velocity model + Snell's law shooting method.
// Map overlay + vertical offset-depth profile for OBN planning.

var _rayState = {
 source: null, // [lat, lon]
 nodes: [], // [{lat, lon, id}]
 results: [], // traced rays
 pickMode: null, // 'source' | 'node' | null
 velMode: 'layered', // constant | gradient | layered | mackenzie
 layers: [{ zBot: 200, v: 1480 }, { zBot: 600, v: 1500 }, { zBot: 1200, v: 1520 }]
};
var _rayPickHandler = null;

function showRayTracing() {
 if (typeof togglePanel === 'function') togglePanel('ray-tracing');
 const modeEl = document.getElementById('ray-vel-mode');
 if (modeEl && _rayState.velMode) modeEl.value = _rayState.velMode;
 raySyncVelocityModeUi();
 rayRenderVModel();
 rayUpdateVelStatus();
 rayUpdateSummary();
 rayDrawProfile();
 if (!layerRayTrace && map) layerRayTrace = L.layerGroup().addTo(map);
}

function rayGetVelMode() {
 const el = document.getElementById('ray-vel-mode');
 const m = el ? el.value : (_rayState.velMode || 'layered');
 return ['constant', 'gradient', 'layered', 'mackenzie'].includes(m) ? m : 'layered';
}

function raySyncVelocityModeUi() {
 const mode = rayGetVelMode();
 _rayState.velMode = mode;
 const blocks = {
  constant: document.getElementById('ray-vel-constant'),
  gradient: document.getElementById('ray-vel-gradient'),
  layered: document.getElementById('ray-vel-layered'),
  mackenzie: document.getElementById('ray-vel-mackenzie')
 };
 Object.keys(blocks).forEach(k => {
  if (blocks[k]) blocks[k].style.display = (k === mode) ? 'block' : 'none';
 });
 const hint = document.getElementById('ray-vel-hint');
 if (hint) {
  const hints = {
   constant: 'Single water velocity from surface to seabed. Fastest check for travel times.',
   gradient: 'Linear V(z) from surface to seabed, discretised into thin layers for Snell’s law.',
   layered: 'Edit layer bottoms (m) and P-velocity (m/s). Full manual 1D water column.',
   mackenzie: 'Mackenzie (1981) approximate sound-speed profile from T, S and depth.'
  };
  hint.textContent = hints[mode] || '';
 }
}

function rayVelocityModeChanged() {
 raySyncVelocityModeUi();
 rayApplyVelocityMode(true);
}

/** Mackenzie (1981) sound speed (m/s): T °C, S psu, D depth km. */
function rayMackenzieSpeed(T, S, depthM) {
 const D = Math.max(0, depthM) / 1000;
 return 1448.96
  + 4.591 * T
  - 5.304e-2 * T * T
  + 2.374e-4 * T * T * T
  + 1.340 * (S - 35)
  + 1.630 * D
  + 1.675e-1 * D * D
  - 1.025e-2 * T * (S - 35)
  - 7.139e-3 * T * D * D;
}

function rayApplyVelocityMode(announce) {
 const mode = rayGetVelMode();
 _rayState.velMode = mode;
 const zr = Math.max(50, parseFloat(document.getElementById('ray-rcv-z')?.value) || 1000);

 if (mode === 'constant') {
  const v = Math.max(100, parseFloat(document.getElementById('ray-vel-const-v')?.value) || 1500);
  _rayState.layers = [{ zBot: zr + 50, v }];
 } else if (mode === 'gradient') {
  const vTop = Math.max(100, parseFloat(document.getElementById('ray-vel-grad-top')?.value) || 1480);
  const vBot = Math.max(100, parseFloat(document.getElementById('ray-vel-grad-bot')?.value) || 1520);
  const n = Math.max(2, Math.min(40, parseInt(document.getElementById('ray-vel-grad-n')?.value, 10) || 8));
  const layers = [];
  for (let i = 1; i <= n; i++) {
   const zBot = (zr * i) / n;
   const midZ = (zr * (i - 0.5)) / n;
   const v = vTop + (vBot - vTop) * (midZ / zr);
   layers.push({ zBot, v: Math.round(v * 10) / 10 });
  }
  _rayState.layers = layers;
 } else if (mode === 'mackenzie') {
  const T = parseFloat(document.getElementById('ray-vel-mac-t')?.value);
  const S = parseFloat(document.getElementById('ray-vel-mac-s')?.value);
  const n = Math.max(2, Math.min(40, parseInt(document.getElementById('ray-vel-mac-n')?.value, 10) || 12));
  const t = isFinite(T) ? T : 10;
  const s = isFinite(S) ? S : 35;
  const layers = [];
  for (let i = 1; i <= n; i++) {
   const zBot = (zr * i) / n;
   const midZ = (zr * (i - 0.5)) / n;
   const v = rayMackenzieSpeed(t, s, midZ);
   layers.push({ zBot, v: Math.round(v * 10) / 10 });
  }
  _rayState.layers = layers;
 }
 // layered: keep existing editable layers

 rayRenderVModel();
 rayUpdateVelStatus();
 rayDrawProfile();
 if (announce) {
  const labels = {
   constant: 'Constant velocity',
   gradient: 'Linear gradient',
   layered: 'Layered 1D',
   mackenzie: 'Mackenzie SSP'
  };
  showToast('Velocity mode: ' + (labels[mode] || mode), 2500);
 }
}

function rayUpdateVelStatus() {
 const el = document.getElementById('ray-vel-mode-status');
 if (!el) return;
 const layers = rayReadLayers();
 if (!layers.length) {
  el.textContent = 'No velocity layers defined.';
  return;
 }
 const vs = layers.map(L => L.v);
 const zMax = layers[layers.length - 1].zBot;
 el.innerHTML = `<span style="color:#fbbf24;font-weight:700;text-transform:uppercase;letter-spacing:0.3px;">${_rayState.velMode}</span>`
  + ` · ${layers.length} layer(s) to ${Math.round(zMax)} m`
  + ` · V ${Math.min(...vs).toFixed(0)}–${Math.max(...vs).toFixed(0)} m/s`;
}

function rayPresetWater() {
 const modeEl = document.getElementById('ray-vel-mode');
 if (modeEl) modeEl.value = 'constant';
 const vEl = document.getElementById('ray-vel-const-v');
 if (vEl) vEl.value = '1500';
 raySyncVelocityModeUi();
 rayApplyVelocityMode(true);
}

function rayPresetGradient() {
 const modeEl = document.getElementById('ray-vel-mode');
 if (modeEl) modeEl.value = 'gradient';
 raySyncVelocityModeUi();
 rayApplyVelocityMode(true);
}

function rayAddLayer() {
 const modeEl = document.getElementById('ray-vel-mode');
 if (modeEl && modeEl.value !== 'layered') {
  modeEl.value = 'layered';
  raySyncVelocityModeUi();
 }
 const last = _rayState.layers[_rayState.layers.length - 1];
 const zBot = (last ? last.zBot : 0) + 200;
 const v = last ? last.v + 20 : 1500;
 _rayState.layers.push({ zBot, v });
 _rayState.velMode = 'layered';
 rayRenderVModel();
 rayUpdateVelStatus();
}

function rayRenderVModel() {
 const host = document.getElementById('ray-vmodel-rows');
 if (!host) return;
 const editable = rayGetVelMode() === 'layered';
 host.innerHTML = _rayState.layers.map((L, i) =>
  `<div style="display:flex;gap:6px;align-items:center;margin-bottom:4px;">
    <span style="width:18px;color:#666;font-size:9px;">${i + 1}</span>
    <input data-ray-i="${i}" data-ray-f="zBot" type="number" min="1" step="10" value="${L.zBot}"
      ${editable ? '' : 'disabled'}
      style="width:70px;padding:3px 5px;border-radius:3px;border:1px solid #333;background:#111;color:#fff;font-size:10px;outline:none;opacity:${editable ? 1 : 0.55};"
      onchange="rayVModelChanged(this)"/>
    <span style="font-size:9px;color:#666;">m</span>
    <input data-ray-i="${i}" data-ray-f="v" type="number" min="100" step="1" value="${L.v}"
      ${editable ? '' : 'disabled'}
      style="width:70px;padding:3px 5px;border-radius:3px;border:1px solid #333;background:#111;color:#fff;font-size:10px;outline:none;opacity:${editable ? 1 : 0.55};"
      onchange="rayVModelChanged(this)"/>
    <span style="font-size:9px;color:#666;">m/s</span>
    ${editable
      ? `<button type="button" onclick="rayRemoveLayer(${i})" style="background:none;border:none;color:#ff453a;cursor:pointer;font-size:12px;" title="Remove">x</button>`
      : ''}
  </div>`
 ).join('');
}

function rayVModelChanged(el) {
 const i = parseInt(el.getAttribute('data-ray-i'), 10);
 const f = el.getAttribute('data-ray-f');
 const v = parseFloat(el.value);
 if (!isFinite(i) || !_rayState.layers[i] || !isFinite(v) || v <= 0) return;
 _rayState.layers[i][f] = v;
 rayUpdateVelStatus();
 rayDrawProfile();
}

function rayRemoveLayer(i) {
 if (_rayState.layers.length <= 1) { showToast('Keep at least one velocity layer'); return; }
 _rayState.layers.splice(i, 1);
 rayRenderVModel();
 rayUpdateVelStatus();
 rayDrawProfile();
}

function rayReadLayers() {
 // Ensure sorted by depth and positive
 const rows = (_rayState.layers || []).map(L => ({
  zBot: Math.max(1, parseFloat(L.zBot) || 1),
  v: Math.max(100, parseFloat(L.v) || 1500)
 })).sort((a, b) => a.zBot - b.zBot);
 // Dedupe / enforce increasing bottoms
 const out = [];
 let prev = 0;
 rows.forEach(L => {
  const zBot = Math.max(prev + 1, L.zBot);
  out.push({ zTop: prev, zBot, v: L.v });
  prev = zBot;
 });
 return out;
}

function rayTraceStopPick() {
 _rayState.pickMode = null;
 if (_rayPickHandler && map) {
  try { map.off('click', _rayPickHandler); } catch (_) {}
 }
 _rayPickHandler = null;
 if (map && map.getContainer) map.getContainer().style.cursor = '';
 const bs = document.getElementById('ray-btn-src');
 const bn = document.getElementById('ray-btn-node');
 if (bs) bs.style.outline = '';
 if (bn) bn.style.outline = '';
}

function rayTracePickSource() {
 rayTraceStopPick();
 if (!map) { showToast('Open the map first'); return; }
 _rayState.pickMode = 'source';
 const bs = document.getElementById('ray-btn-src');
 if (bs) bs.style.outline = '2px solid #fff';
 map.getContainer().style.cursor = 'crosshair';
 showToast('Click map to place the source (gun / source vessel)', 4000);
 _rayPickHandler = (e) => {
  _rayState.source = [e.latlng.lat, e.latlng.lng];
  rayTraceStopPick();
  rayRedrawMapGraphics();
  rayUpdateSummary();
  showToast('Source placed', 2500);
 };
 map.on('click', _rayPickHandler);
}

function rayTracePickNode() {
 rayTraceStopPick();
 if (!map) { showToast('Open the map first'); return; }
 _rayState.pickMode = 'node';
 const bn = document.getElementById('ray-btn-node');
 if (bn) bn.style.outline = '2px solid #fff';
 map.getContainer().style.cursor = 'crosshair';
 showToast('Click map to place an OBN node (repeat as needed)', 4000);
 _rayPickHandler = (e) => {
  _rayState.nodes.push({
   id: _rayState.nodes.length + 1,
   lat: e.latlng.lat,
   lon: e.latlng.lng
  });
  rayRedrawMapGraphics();
  rayUpdateSummary();
  showToast(`Node ${_rayState.nodes.length} placed`, 2000);
 };
 map.on('click', _rayPickHandler);
}

function rayGeneratePatch() {
 if (!_rayState.source) {
  showToast('Place a source first (or click the map centre will be used)');
 }
 const nx = Math.max(1, Math.min(40, parseInt(document.getElementById('ray-patch-nx')?.value, 10) || 5));
 const ny = Math.max(1, Math.min(40, parseInt(document.getElementById('ray-patch-ny')?.value, 10) || 5));
 const dx = Math.max(10, parseFloat(document.getElementById('ray-patch-dx')?.value) || 400);
 let origin = _rayState.source;
 if (!origin && map) {
  const c = map.getCenter();
  origin = [c.lat, c.lng];
  _rayState.source = origin.slice();
 }
 if (!origin) { showToast('Need a map centre or source'); return; }

 // Patch centred on source (east/north offsets in metres)
 const nodes = [];
 const x0 = -((nx - 1) * dx) / 2;
 const y0 = -((ny - 1) * dx) / 2;
 for (let iy = 0; iy < ny; iy++) {
  for (let ix = 0; ix < nx; ix++) {
   const east = x0 + ix * dx;
   const north = y0 + iy * dx;
   // Move east then north from origin
   const p1 = destinationPoint(origin, 90, east);
   const p2 = destinationPoint(p1, 0, north);
   nodes.push({ id: nodes.length + 1, lat: p2[0], lon: p2[1] });
  }
 }
 _rayState.nodes = nodes;
 rayRedrawMapGraphics();
 rayUpdateSummary();
 showToast(`Generated ${nodes.length}-node patch @ ${dx} m`, 3500);
}

/**
 * Propagate a ray with ray parameter p = sin(theta)/v through layered model
 * from zs to zr. Returns { ok, offsetM, timeSec, path:[{z,x,v,theta}] }.
 */
function rayPropagate(p, layers, zs, zr) {
 if (!(zr > zs)) return { ok: false, reason: 'receiver_above_source' };
 const path = [{ z: zs, x: 0, v: null, theta: null }];
 let x = 0, t = 0;
 let z = zs;

 for (let i = 0; i < layers.length; i++) {
  const L = layers[i];
  if (L.zBot <= z) continue;
  const zEnter = Math.max(z, L.zTop);
  const zLeave = Math.min(zr, L.zBot);
  if (zLeave <= zEnter) continue;

  const arg = p * L.v;
  if (arg >= 1) {
   // Turning / critical in this layer - cannot continue downward
   return { ok: false, reason: 'critical', offsetM: x, timeSec: t, path };
  }
  const theta = Math.asin(arg); // from vertical
  const dz = zLeave - zEnter;
  const cosT = Math.cos(theta);
  if (cosT < 1e-9) return { ok: false, reason: 'horizontal', offsetM: x, timeSec: t, path };
  const dx = dz * Math.tan(theta);
  const dt = dz / (L.v * cosT);
  x += dx;
  t += dt;
  z = zLeave;
  path.push({ z, x, v: L.v, theta: theta * 180 / Math.PI });
  if (z >= zr - 1e-6) break;
 }

 if (z < zr - 0.5) {
  // Model too shallow - extend last velocity
  const v = layers.length ? layers[layers.length - 1].v : 1500;
  const arg = p * v;
  if (arg >= 1) return { ok: false, reason: 'critical', offsetM: x, timeSec: t, path };
  const theta = Math.asin(arg);
  const dz = zr - z;
  const cosT = Math.cos(theta);
  x += dz * Math.tan(theta);
  t += dz / (v * cosT);
  path.push({ z: zr, x, v, theta: theta * 180 / Math.PI });
 }

 return { ok: true, offsetM: x, timeSec: t, path, p };
}

/** Shoot a ray from (zs) to hit horizontal offset X at depth zr. */
function rayShoot(layers, zs, zr, targetOffsetM) {
 const X = Math.abs(targetOffsetM);
 if (X < 1) {
  // Vertical
  let t = 0, z = zs;
  const path = [{ z: zs, x: 0 }];
  for (const L of layers) {
   if (L.zBot <= z) continue;
   const z0 = Math.max(z, L.zTop);
   const z1 = Math.min(zr, L.zBot);
   if (z1 <= z0) continue;
   t += (z1 - z0) / L.v;
   z = z1;
   path.push({ z, x: 0, v: L.v, theta: 0 });
   if (z >= zr) break;
  }
  if (z < zr) {
   const v = layers.length ? layers[layers.length - 1].v : 1500;
   t += (zr - z) / v;
   path.push({ z: zr, x: 0, v, theta: 0 });
  }
  return { ok: true, offsetM: 0, timeSec: t, path, takeoffDeg: 0, p: 0 };
 }

 // p ranges from 0 (vertical) to almost 1/vmin
 const vmin = Math.min(...layers.map(L => L.v), 1500);
 let lo = 0, hi = (1 / vmin) * 0.999;
 let best = null;
 for (let iter = 0; iter < 48; iter++) {
  const mid = 0.5 * (lo + hi);
  const r = rayPropagate(mid, layers, zs, zr);
  if (!r.ok) { hi = mid; continue; }
  best = r;
  if (r.offsetM > X) hi = mid;
  else lo = mid;
  if (Math.abs(r.offsetM - X) < 0.5) break;
 }
 if (!best || !best.ok) return { ok: false, reason: 'no_solution' };
 // Scale path x to exact target (small correction) if close
 const scale = best.offsetM > 1e-6 ? X / best.offsetM : 1;
 if (Math.abs(scale - 1) < 0.05) {
  best.path = best.path.map(pt => ({ ...pt, x: (pt.x || 0) * scale }));
  best.offsetM = X;
 }
 const takeoff = best.path.find(pt => pt.theta != null);
 best.takeoffDeg = takeoff ? takeoff.theta : (Math.asin(Math.min(0.999, best.p * vmin)) * 180 / Math.PI);
 return best;
}

function rayTraceRun() {
 rayTraceStopPick();
 if (!_rayState.source) { showToast('Place a source first'); return; }
 if (!_rayState.nodes.length) { showToast('Place or generate at least one node'); return; }

 // Rebuild generated modes from current geometry / params before shooting
 if (rayGetVelMode() !== 'layered') rayApplyVelocityMode(false);

 const zs = Math.max(0, parseFloat(document.getElementById('ray-src-z')?.value) || 8);
 const zr = Math.max(zs + 1, parseFloat(document.getElementById('ray-rcv-z')?.value) || 1000);
 const maxOff = Math.max(100, parseFloat(document.getElementById('ray-max-off')?.value) || 8000);
 const maxDraw = Math.max(1, Math.min(500, parseInt(document.getElementById('ray-max-draw')?.value, 10) || 80));
 const layers = rayReadLayers();
 // Ensure model covers receiver depth
 if (!layers.length || layers[layers.length - 1].zBot < zr) {
  const v = layers.length ? layers[layers.length - 1].v : 1500;
  const zTop = layers.length ? layers[layers.length - 1].zBot : 0;
  layers.push({ zTop, zBot: zr + 10, v });
 }

 const results = [];
 for (const node of _rayState.nodes) {
  const off = haversine(_rayState.source, [node.lat, node.lon]);
  if (off > maxOff) continue;
  const shot = rayShoot(layers, zs, zr, off);
  if (!shot.ok) continue;
  const brng = bearing(_rayState.source, [node.lat, node.lon]);
  // Build geographic polyline along bearing using path offsets
  const latlngs = shot.path.map(pt => {
   const d = Math.abs(pt.x || 0);
   if (d < 0.5) return _rayState.source.slice();
   return destinationPoint(_rayState.source, brng, d);
  });
  results.push({
   nodeId: node.id,
   offsetM: off,
   timeSec: shot.timeSec,
   takeoffDeg: shot.takeoffDeg,
   path: shot.path,
   latlngs,
   node: [node.lat, node.lon]
  });
 }

 results.sort((a, b) => a.offsetM - b.offsetM);
 _rayState.results = results.slice(0, maxDraw);
 if (results.length > maxDraw) {
  showToast(`Traced ${results.length} rays - drawing first ${maxDraw} (raise Max rays to see more)`, 5000);
 } else if (!results.length) {
  showToast('No rays reached nodes - check depths, max offset, or velocity model', 6000);
 } else {
  showToast(`Traced ${_rayState.results.length} ray(s)`, 3000);
 }
 rayRedrawMapGraphics();
 rayDrawProfile();
 rayUpdateSummary();
}

function rayTraceClear() {
 rayTraceStopPick();
 _rayState.source = null;
 _rayState.nodes = [];
 _rayState.results = [];
 if (layerRayTrace) layerRayTrace.clearLayers();
 rayUpdateSummary();
 rayDrawProfile();
 showToast('Ray tracing cleared');
}

function rayTimeColor(t, tMin, tMax) {
 if (!(tMax > tMin)) return '#fbbf24';
 const u = Math.max(0, Math.min(1, (t - tMin) / (tMax - tMin)));
 // yellow -> orange -> red
 const r = Math.round(251 + (239 - 251) * u);
 const g = Math.round(191 * (1 - u));
 const b = Math.round(36 * (1 - u));
 return `rgb(${r},${g},${b})`;
}

function rayRedrawMapGraphics() {
 if (!map) return;
 if (!layerRayTrace) layerRayTrace = L.layerGroup().addTo(map);
 layerRayTrace.clearLayers();

 if (_rayState.source) {
  L.circleMarker(_rayState.source, {
   radius: 7, color: '#fff', weight: 2, fillColor: '#f59e0b', fillOpacity: 1
  }).bindTooltip('Source', { permanent: false }).addTo(layerRayTrace);
 }

 _rayState.nodes.forEach(n => {
  L.circleMarker([n.lat, n.lon], {
   radius: 5, color: '#0ea5e9', weight: 1, fillColor: '#38bdf8', fillOpacity: 0.95
  }).bindTooltip('Node ' + n.id, { permanent: false }).addTo(layerRayTrace);
 });

 const times = _rayState.results.map(r => r.timeSec);
 const tMin = times.length ? Math.min(...times) : 0;
 const tMax = times.length ? Math.max(...times) : 1;
 _rayState.results.forEach(r => {
  const col = rayTimeColor(r.timeSec, tMin, tMax);
  L.polyline(r.latlngs, {
   color: col, weight: 2, opacity: 0.85, interactive: false
  }).addTo(layerRayTrace);
 });
}

function rayUpdateSummary() {
 const el = document.getElementById('ray-summary');
 if (!el) return;
 const nSrc = _rayState.source ? 1 : 0;
 const nNodes = _rayState.nodes.length;
 const nRays = _rayState.results.length;
 if (!nSrc && !nNodes) {
  el.textContent = 'No rays yet - place a source and at least one node, then Trace Rays.';
  return;
 }
 let html = `<strong style="color:#fbbf24;">${nSrc}</strong> source · <strong style="color:#38bdf8;">${nNodes}</strong> node(s) · <strong style="color:#30d158;">${nRays}</strong> ray(s)`
  + ` · vel <strong style="color:#fbbf24;">${_rayState.velMode || rayGetVelMode()}</strong>`;
 if (nRays) {
  const times = _rayState.results.map(r => r.timeSec);
  const offs = _rayState.results.map(r => r.offsetM);
  html += `<br>Offset ${Math.min(...offs).toFixed(0)}-${Math.max(...offs).toFixed(0)} m · ` +
   `Travel time ${(Math.min(...times)).toFixed(3)}-${(Math.max(...times)).toFixed(3)} s · ` +
   `Takeoff ${Math.min(..._rayState.results.map(r => r.takeoffDeg)).toFixed(1)}-${Math.max(..._rayState.results.map(r => r.takeoffDeg)).toFixed(1)} deg from vertical`;
 }
 el.innerHTML = html;
}

function rayDrawProfile() {
 const canvas = document.getElementById('ray-profile-canvas');
 if (!canvas) return;
 const ctx = canvas.getContext('2d');
 const W = canvas.width, H = canvas.height;
 ctx.clearRect(0, 0, W, H);
 ctx.fillStyle = '#07070c';
 ctx.fillRect(0, 0, W, H);

 const zs = Math.max(0, parseFloat(document.getElementById('ray-src-z')?.value) || 8);
 const zr = Math.max(zs + 1, parseFloat(document.getElementById('ray-rcv-z')?.value) || 1000);
 const results = _rayState.results || [];
 const maxX = results.length
  ? Math.max(100, ...results.map(r => r.offsetM))
  : (parseFloat(document.getElementById('ray-max-off')?.value) || 8000);
 const padL = 48, padR = 16, padT = 16, padB = 36;
 const plotW = W - padL - padR;
 const plotH = H - padT - padB;

 const xToPx = (x) => padL + (x / maxX) * plotW;
 const zToPx = (z) => padT + ((z - 0) / zr) * plotH;

 // Grid
 ctx.strokeStyle = '#1a1a24';
 ctx.lineWidth = 1;
 for (let i = 0; i <= 4; i++) {
  const z = (zr * i) / 4;
  const y = zToPx(z);
  ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
  ctx.fillStyle = '#666';
  ctx.font = '10px sans-serif';
  ctx.fillText(Math.round(z) + ' m', 4, y + 3);
 }
 for (let i = 0; i <= 4; i++) {
  const x = (maxX * i) / 4;
  const px = xToPx(x);
  ctx.beginPath(); ctx.moveTo(px, padT); ctx.lineTo(px, H - padB); ctx.stroke();
  ctx.fillStyle = '#666';
  ctx.fillText(Math.round(x) + ' m', px - 10, H - 12);
 }

 // Seabed line
 ctx.strokeStyle = '#334155';
 ctx.setLineDash([4, 3]);
 ctx.beginPath(); ctx.moveTo(padL, zToPx(zr)); ctx.lineTo(W - padR, zToPx(zr)); ctx.stroke();
 ctx.setLineDash([]);

 // Velocity layer boundaries
 const layers = rayReadLayers();
 ctx.strokeStyle = '#1e293b';
 layers.forEach(L => {
  if (L.zBot >= zr) return;
  const y = zToPx(L.zBot);
  ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
 });

 if (!results.length) {
  ctx.fillStyle = '#556';
  ctx.font = '12px sans-serif';
  ctx.fillText('Trace rays to populate the profile', padL + 12, padT + 24);
  return;
 }

 const times = results.map(r => r.timeSec);
 const tMin = Math.min(...times), tMax = Math.max(...times);
 results.forEach(r => {
  ctx.strokeStyle = rayTimeColor(r.timeSec, tMin, tMax);
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  r.path.forEach((pt, i) => {
   const px = xToPx(Math.abs(pt.x || 0));
   const py = zToPx(pt.z);
   if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
  });
  ctx.stroke();
 });

 // Source marker
 ctx.fillStyle = '#f59e0b';
 ctx.beginPath();
 ctx.arc(xToPx(0), zToPx(zs), 4, 0, Math.PI * 2);
 ctx.fill();
}
