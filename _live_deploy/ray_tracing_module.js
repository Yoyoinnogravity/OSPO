// ===== ACOUSTIC RAY TRACING (OBN / water-column) =====
// Velocity Mode: constant | gradient | layered | mackenzie
// Layered 1D water-column model + Snell's-law shooting.
// Water-column only (not NORSAR / ACTeQ subsurface illumination).
// Map overlay + vertical offset-depth profile for OBN planning.

var _rayState = {
 source: null, // [lat, lon]
 nodes: [], // [{lat, lon, id, name?}]
 results: [], // drawn rays (may be capped)
 allResults: [], // full compute set
 skipped: { maxOffset: 0, critical: 0, failed: 0 },
 pickMode: null, // 'source' | 'node' | null
 velMode: 'layered', // constant | gradient | layered | mackenzie
 layers: [{ zBot: 200, v: 1480 }, { zBot: 600, v: 1500 }, { zBot: 1200, v: 1520 }],
 velConfirmed: false, // user accepted a velocity field via ask dialog
 busy: false,
 lastRunAt: null
};
var _rayPickHandler = null;
var _rayTraceToken = 0;

function showRayTracing() {
 if (typeof togglePanel === 'function') togglePanel('ray-tracing');
 const modeEl = document.getElementById('ray-vel-mode');
 if (modeEl && _rayState.velMode) modeEl.value = _rayState.velMode;
 raySyncVelocityModeUi();
 rayRenderVModel();
 rayUpdateVelStatus();
 rayUpdateSummary();
 rayRenderResultsTable();
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
   constant: 'Single water velocity from surface to seabed. Exact straight-ray travel times.',
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
  const n = Math.max(2, Math.min(80, parseInt(document.getElementById('ray-vel-grad-n')?.value, 10) || 8));
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
  const n = Math.max(2, Math.min(80, parseInt(document.getElementById('ray-vel-mac-n')?.value, 10) || 12));
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
 if (typeof velFieldSyncStatusUi === 'function') velFieldSyncStatusUi();
 else {
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
 const rows = (_rayState.layers || []).map(L => ({
  zBot: Math.max(1, parseFloat(L.zBot) || 1),
  v: Math.max(100, parseFloat(L.v) || 1500)
 })).sort((a, b) => a.zBot - b.zBot);
 const out = [];
 let prev = 0;
 rows.forEach(L => {
  const zBot = Math.max(prev + 1, L.zBot);
  out.push({ zTop: prev, zBot, v: L.v });
  prev = zBot;
 });
 return out;
}

function rayEnsureModelCovers(layers, zr) {
 const L = layers.slice();
 if (!L.length || L[L.length - 1].zBot < zr) {
  const v = L.length ? L[L.length - 1].v : 1500;
  const zTop = L.length ? L[L.length - 1].zBot : 0;
  L.push({ zTop, zBot: zr + 10, v });
 }
 return L;
}

function rayVAtDepth(layers, z) {
 const L = layers || [];
 for (let i = 0; i < L.length; i++) {
  if (z <= L[i].zBot + 1e-6) return L[i].v;
 }
 return L.length ? L[L.length - 1].v : 1500;
}

/**
 * Flat-horizon specular image point through a 1D V(z) field (Snell p shared on both legs).
 * Falls back to CMP when the target coincides with a station depth.
 */
function raySpecularImagePoint(sx, sy, zs, rx, ry, zr, Z, layers) {
 const off = Math.hypot(rx - sx, ry - sy);
 if (!(isFinite(off))) return { x: sx, y: sy, offset: 0, method: 'bad', p: 0, incDeg: 0 };
 // Classic CMP when target ≈ receiver depth, or stations at same depth with tiny offset
 if (Math.abs(Z - zr) < 1 || (Math.abs(zs - zr) < 0.5 && Math.abs(Z - zs) < 1)) {
  return { x: (sx + rx) / 2, y: (sy + ry) / 2, offset: off, method: 'cmp', p: 0, incDeg: 0 };
 }
 if (!(Z > zs + 0.5) || !(Z > zr + 0.5)) {
  const h1 = Math.max(1e-3, Math.abs(Z - zs));
  const h2 = Math.max(1e-3, Math.abs(Z - zr));
  const w = h1 / (h1 + h2);
  return {
   x: sx + (rx - sx) * w,
   y: sy + (ry - sy) * w,
   offset: off,
   method: 'depth_weight',
   p: 0,
   incDeg: Math.atan2(off / 2, Math.max(1e-3, Z - Math.min(zs, zr))) * 180 / Math.PI
  };
 }
 if (off < 1) {
  return { x: sx, y: sy, offset: 0, method: 'vertical', p: 0, incDeg: 0 };
 }

 const L = rayEnsureModelCovers(layers || rayReadLayers(), Z + 20);
 const vmin = Math.min(...L.map(l => l.v), 1500);
 let lo = 0, hi = (1 / vmin) * 0.999;
 let best = null;
 for (let iter = 0; iter < 72; iter++) {
  const mid = 0.5 * (lo + hi);
  const ds = rayPropagate(mid, L, zs, Z);
  const dr = rayPropagate(mid, L, zr, Z);
  if (!ds.ok || !dr.ok) { hi = mid; continue; }
  const sum = ds.offsetM + dr.offsetM;
  best = { p: mid, xs: ds.offsetM, xr: dr.offsetM, sum };
  if (sum > off) hi = mid;
  else lo = mid;
  if (Math.abs(sum - off) < 0.4) break;
 }
 if (!best || !(best.sum > 1e-6)) {
  const h1 = Math.max(1e-3, Z - zs);
  const h2 = Math.max(1e-3, Z - zr);
  const w = h1 / (h1 + h2);
  return {
   x: sx + (rx - sx) * w,
   y: sy + (ry - sy) * w,
   offset: off,
   method: 'fallback',
   p: 0,
   incDeg: Math.atan2(off / 2, h1) * 180 / Math.PI
  };
 }
 const scale = off / best.sum;
 const xs = best.xs * scale;
 const ux = (rx - sx) / off, uy = (ry - sy) / off;
 const vZ = rayVAtDepth(L, Z);
 const arg = Math.min(0.999999, Math.max(0, best.p * vZ));
 const incDeg = Math.asin(arg) * 180 / Math.PI;
 return {
  x: sx + ux * xs,
  y: sy + uy * xs,
  offset: off,
  method: 'snell',
  p: best.p,
  xs,
  xr: best.xr * scale,
  incDeg
 };
}

function velFieldGetLayers(coverZ) {
 if (typeof rayGetVelMode === 'function' && rayGetVelMode() !== 'layered') {
  try { rayApplyVelocityMode(false); } catch (_) {}
 }
 return rayEnsureModelCovers(rayReadLayers(), Math.max(50, coverZ || 1000));
}

function velFieldStatusText() {
 const layers = rayReadLayers();
 if (!layers.length) return 'No velocity field set';
 const vs = layers.map(L => L.v);
 const zMax = layers[layers.length - 1].zBot;
 const conf = _rayState.velConfirmed ? 'ready' : 'not confirmed';
 return (_rayState.velMode || 'layered')
  + ' · ' + layers.length + ' layer(s) to ' + Math.round(zMax) + ' m'
  + ' · V ' + Math.min(...vs).toFixed(0) + '–' + Math.max(...vs).toFixed(0) + ' m/s'
  + ' · ' + conf;
}

function velFieldSyncStatusUi() {
 const t = velFieldStatusText();
 const a = document.getElementById('ray-vel-mode-status');
 if (a) {
  const layers = rayReadLayers();
  if (!layers.length) a.textContent = 'No velocity layers defined.';
  else {
   const vs = layers.map(L => L.v);
   const zMax = layers[layers.length - 1].zBot;
   a.innerHTML = `<span style="color:#fbbf24;font-weight:700;text-transform:uppercase;letter-spacing:0.3px;">${_rayState.velMode || 'layered'}</span>`
    + ` · ${layers.length} layer(s) to ${Math.round(zMax)} m`
    + ` · V ${Math.min(...vs).toFixed(0)}–${Math.max(...vs).toFixed(0)} m/s`
    + (_rayState.velConfirmed
      ? ' · <span style="color:#30d158;">confirmed</span>'
      : ' · <span style="color:#fbbf24;">ask to confirm</span>');
  }
 }
 const b = document.getElementById('fold-vel-status');
 if (b) b.textContent = t;
}

function velFieldParseCsv(text) {
 const rows = [];
 String(text || '').split(/\r?\n/).forEach(line => {
  const s = line.trim();
  if (!s || s[0] === '#' || s[0] === ';') return;
  const parts = s.split(/[,;\s\t]+/).map(Number).filter(n => isFinite(n));
  if (parts.length >= 2) rows.push({ zBot: parts[0], v: parts[1] });
 });
 rows.sort((a, b) => a.zBot - b.zBot);
 return rows.filter(r => r.zBot > 0 && r.v > 50);
}

/**
 * Ask the user for a 1D velocity field (modal). Resolves true if applied.
 * Shared by ray tracing and fold-at-depth.
 */
function velFieldAsk(opts) {
 const o = opts || {};
 const coverSuggest = Math.max(50, parseFloat(o.coverZ) || parseFloat(document.getElementById('fold-synth-depth')?.value)
  || parseFloat(document.getElementById('ray-rcv-z')?.value) || 1000);
 const title = o.title || 'Velocity field';
 const reason = o.reason || 'Used for Snell ray tracing and fold image points at depth.';

 return new Promise((resolve) => {
  const existing = document.getElementById('vel-field-ask-overlay');
  if (existing) existing.remove();

  const mode0 = _rayState.velMode || rayGetVelMode() || 'layered';
  const overlay = document.createElement('div');
  overlay.id = 'vel-field-ask-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;z-index:10050;background:rgba(0,0,0,0.72);display:flex;align-items:center;justify-content:center;padding:16px;';
  overlay.innerHTML = `
   <div style="width:min(520px,96vw);max-height:90vh;overflow:auto;background:#0c0c14;border:1px solid #334155;border-radius:10px;padding:16px 18px;box-shadow:0 20px 50px rgba(0,0,0,0.55);">
    <div style="font-size:14px;font-weight:800;color:#fbbf24;margin-bottom:6px;">${title}</div>
    <div style="font-size:11px;color:#94a3b8;line-height:1.45;margin-bottom:12px;">${reason}<br/>Enter a 1D V(z) water-column (or extended) field, then confirm.</div>
    <label style="display:flex;align-items:center;gap:8px;font-size:11px;color:#cbd5e1;margin-bottom:10px;">Mode
     <select id="vf-ask-mode" style="flex:1;padding:6px 8px;border-radius:4px;border:1px solid #f59e0b;background:#111;color:#fbbf24;font-weight:700;font-size:11px;outline:none;">
      <option value="constant">Constant</option>
      <option value="gradient">Linear gradient</option>
      <option value="layered">Layered 1D / CSV</option>
      <option value="mackenzie">Mackenzie SSP</option>
     </select>
    </label>
    <label style="display:flex;align-items:center;gap:8px;font-size:11px;color:#cbd5e1;margin-bottom:10px;">Cover to depth
     <input id="vf-ask-cover" type="number" min="10" step="10" value="${Math.round(coverSuggest)}"
      style="width:90px;padding:5px 6px;border-radius:4px;border:1px solid #333;background:#111;color:#fff;font-size:11px;outline:none;"/> m
    </label>
    <div id="vf-ask-constant" style="display:none;margin-bottom:10px;">
     <label style="font-size:11px;color:#94a3b8;">V <input id="vf-ask-const-v" type="number" min="100" step="1" value="1500"
      style="width:90px;margin-left:6px;padding:5px 6px;border-radius:4px;border:1px solid #333;background:#111;color:#fff;font-size:11px;outline:none;"/> m/s</label>
    </div>
    <div id="vf-ask-gradient" style="display:none;margin-bottom:10px;">
     <div style="display:flex;flex-wrap:wrap;gap:10px;font-size:11px;color:#94a3b8;">
      <label>V top <input id="vf-ask-grad-top" type="number" value="1480" style="width:72px;margin-left:4px;padding:4px;border-radius:3px;border:1px solid #333;background:#111;color:#fff;font-size:11px;"/></label>
      <label>V bottom <input id="vf-ask-grad-bot" type="number" value="1520" style="width:72px;margin-left:4px;padding:4px;border-radius:3px;border:1px solid #333;background:#111;color:#fff;font-size:11px;"/></label>
      <label>Layers <input id="vf-ask-grad-n" type="number" min="2" max="80" value="8" style="width:52px;margin-left:4px;padding:4px;border-radius:3px;border:1px solid #333;background:#111;color:#fff;font-size:11px;"/></label>
     </div>
    </div>
    <div id="vf-ask-mackenzie" style="display:none;margin-bottom:10px;">
     <div style="display:flex;flex-wrap:wrap;gap:10px;font-size:11px;color:#94a3b8;">
      <label>T °C <input id="vf-ask-mac-t" type="number" value="10" step="0.1" style="width:60px;margin-left:4px;padding:4px;border-radius:3px;border:1px solid #333;background:#111;color:#fff;font-size:11px;"/></label>
      <label>S psu <input id="vf-ask-mac-s" type="number" value="35" step="0.1" style="width:60px;margin-left:4px;padding:4px;border-radius:3px;border:1px solid #333;background:#111;color:#fff;font-size:11px;"/></label>
      <label>Layers <input id="vf-ask-mac-n" type="number" min="2" max="80" value="12" style="width:52px;margin-left:4px;padding:4px;border-radius:3px;border:1px solid #333;background:#111;color:#fff;font-size:11px;"/></label>
     </div>
    </div>
    <div id="vf-ask-layered" style="margin-bottom:10px;">
     <div style="font-size:10px;color:#64748b;margin-bottom:6px;">Paste CSV: <code style="color:#94a3b8;">depth_m, v_mps</code> (layer bottoms). Leave blank to keep the current layered table.</div>
     <textarea id="vf-ask-csv" rows="5" placeholder="# zBot_m, v_mps&#10;200,1480&#10;600,1500&#10;1200,1520"
      style="width:100%;box-sizing:border-box;padding:8px;border-radius:4px;border:1px solid #333;background:#0a0a12;color:#e2e8f0;font-size:11px;font-family:ui-monospace,monospace;resize:vertical;outline:none;"></textarea>
     <div style="font-size:9px;color:#556;margin-top:4px;">Current: ${(_rayState.layers || []).map(L => L.zBot + 'm@' + L.v).join(' · ') || 'none'}</div>
    </div>
    <div id="vf-ask-preview" style="font-size:10px;color:#64748b;margin-bottom:12px;min-height:1.2em;"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;">
     <button type="button" id="vf-ask-cancel" style="padding:7px 14px;border-radius:4px;border:1px solid #333;background:#1a1a2e;color:#94a3b8;font-weight:700;cursor:pointer;font-size:11px;">Cancel</button>
     <button type="button" id="vf-ask-ok" style="padding:7px 16px;border-radius:4px;border:none;background:#f59e0b;color:#111;font-weight:800;cursor:pointer;font-size:11px;">Use velocity field</button>
    </div>
  </div>`;
  document.body.appendChild(overlay);

  const set = (id, v) => { const el = document.getElementById(id); if (el && v != null && isFinite(v)) el.value = v; };
  // Prefill from ray panel if present
  set('vf-ask-const-v', parseFloat(document.getElementById('ray-vel-const-v')?.value) || 1500);
  set('vf-ask-grad-top', parseFloat(document.getElementById('ray-vel-grad-top')?.value) || 1480);
  set('vf-ask-grad-bot', parseFloat(document.getElementById('ray-vel-grad-bot')?.value) || 1520);
  set('vf-ask-grad-n', parseInt(document.getElementById('ray-vel-grad-n')?.value, 10) || 8);
  set('vf-ask-mac-t', parseFloat(document.getElementById('ray-vel-mac-t')?.value) || 10);
  set('vf-ask-mac-s', parseFloat(document.getElementById('ray-vel-mac-s')?.value) || 35);
  set('vf-ask-mac-n', parseInt(document.getElementById('ray-vel-mac-n')?.value, 10) || 12);

  const modeEl = document.getElementById('vf-ask-mode');
  if (modeEl) modeEl.value = mode0;

  function syncBlocks() {
   const m = modeEl.value;
   ['constant', 'gradient', 'layered', 'mackenzie'].forEach(k => {
    const el = document.getElementById('vf-ask-' + k);
    if (el) el.style.display = (k === m) ? 'block' : 'none';
   });
  }
  syncBlocks();
  modeEl.onchange = syncBlocks;

  function finish(ok) {
   overlay.remove();
   resolve(!!ok);
  }
  document.getElementById('vf-ask-cancel').onclick = () => finish(false);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) finish(false); });

  document.getElementById('vf-ask-ok').onclick = () => {
   const mode = modeEl.value;
   const cover = Math.max(50, parseFloat(document.getElementById('vf-ask-cover')?.value) || coverSuggest);
   let layers = [];

   if (mode === 'constant') {
    const v = Math.max(100, parseFloat(document.getElementById('vf-ask-const-v')?.value) || 1500);
    layers = [{ zBot: cover + 50, v }];
    const el = document.getElementById('ray-vel-const-v'); if (el) el.value = String(v);
   } else if (mode === 'gradient') {
    const vTop = Math.max(100, parseFloat(document.getElementById('vf-ask-grad-top')?.value) || 1480);
    const vBot = Math.max(100, parseFloat(document.getElementById('vf-ask-grad-bot')?.value) || 1520);
    const n = Math.max(2, Math.min(80, parseInt(document.getElementById('vf-ask-grad-n')?.value, 10) || 8));
    for (let i = 1; i <= n; i++) {
     const zBot = (cover * i) / n;
     const midZ = (cover * (i - 0.5)) / n;
     const v = vTop + (vBot - vTop) * (midZ / cover);
     layers.push({ zBot, v: Math.round(v * 10) / 10 });
    }
    set('ray-vel-grad-top', vTop); set('ray-vel-grad-bot', vBot); set('ray-vel-grad-n', n);
   } else if (mode === 'mackenzie') {
    const T = parseFloat(document.getElementById('vf-ask-mac-t')?.value);
    const S = parseFloat(document.getElementById('vf-ask-mac-s')?.value);
    const n = Math.max(2, Math.min(80, parseInt(document.getElementById('vf-ask-mac-n')?.value, 10) || 12));
    const t = isFinite(T) ? T : 10;
    const s = isFinite(S) ? S : 35;
    for (let i = 1; i <= n; i++) {
     const zBot = (cover * i) / n;
     const midZ = (cover * (i - 0.5)) / n;
     layers.push({ zBot, v: Math.round(rayMackenzieSpeed(t, s, midZ) * 10) / 10 });
    }
    set('ray-vel-mac-t', t); set('ray-vel-mac-s', s); set('ray-vel-mac-n', n);
   } else {
    const csv = document.getElementById('vf-ask-csv')?.value || '';
    const parsed = velFieldParseCsv(csv);
    if (parsed.length) layers = parsed;
    else layers = (_rayState.layers || []).map(L => ({ zBot: L.zBot, v: L.v }));
    if (!layers.length) layers = [{ zBot: cover + 50, v: 1500 }];
    // Extend last layer if CSV stops above cover
    if (layers[layers.length - 1].zBot < cover) {
     layers.push({ zBot: cover + 10, v: layers[layers.length - 1].v });
    }
   }

   _rayState.layers = layers;
   _rayState.velMode = mode;
   _rayState.velConfirmed = true;
   const modeUi = document.getElementById('ray-vel-mode');
   if (modeUi) modeUi.value = mode;
   try {
    raySyncVelocityModeUi();
    rayRenderVModel();
    rayUpdateVelStatus();
    rayDrawProfile();
   } catch (_) {}
   velFieldSyncStatusUi();
   if (typeof showToast === 'function') {
    showToast('Velocity field set: ' + mode + ' · ' + layers.length + ' layer(s) to ~'
     + Math.round(layers[layers.length - 1].zBot) + ' m', 3500);
   }
   finish(true);
  };
 });
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
 if (!map) { showToast('Open the Design map first'); return; }
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
 if (!map) { showToast('Open the Design map first'); return; }
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

/** Import seabed nodes from OBN preplot / state.obnNodes. */
function rayImportObnNodes() {
 const fromState = (typeof state !== 'undefined' && Array.isArray(state.obnNodes))
  ? state.obnNodes
  : [];
 if (!fromState.length) {
  showToast('No OBN preplot nodes found — generate an OBN layout in Design first', 5000);
  return;
 }
 _rayState.nodes = fromState.map((n, i) => ({
  id: n.id != null ? n.id : (i + 1),
  name: n.name || ('N' + (i + 1)),
  lat: Number(n.lat),
  lon: Number(n.lon)
 })).filter(n => isFinite(n.lat) && isFinite(n.lon));

 if (!_rayState.source && map) {
  // Use patch centroid as a default source if none placed
  let slat = 0, slon = 0;
  _rayState.nodes.forEach(n => { slat += n.lat; slon += n.lon; });
  _rayState.source = [slat / _rayState.nodes.length, slon / _rayState.nodes.length];
 }

 rayRedrawMapGraphics();
 rayUpdateSummary();
 rayFitMap();
 showToast('Imported ' + _rayState.nodes.length + ' OBN node(s)'
  + (_rayState.source ? ' · source at patch centre (move if needed)' : ''), 4500);
}

function rayGeneratePatch() {
 if (!_rayState.source) {
  showToast('Place a source first (or map centre will be used)');
 }
 const nx = Math.max(1, Math.min(60, parseInt(document.getElementById('ray-patch-nx')?.value, 10) || 5));
 const ny = Math.max(1, Math.min(60, parseInt(document.getElementById('ray-patch-ny')?.value, 10) || 5));
 const dx = Math.max(10, parseFloat(document.getElementById('ray-patch-dx')?.value) || 400);
 let origin = _rayState.source;
 if (!origin && map) {
  const c = map.getCenter();
  origin = [c.lat, c.lng];
  _rayState.source = origin.slice();
 }
 if (!origin) { showToast('Need a map centre or source'); return; }

 const nodes = [];
 const x0 = -((nx - 1) * dx) / 2;
 const y0 = -((ny - 1) * dx) / 2;
 for (let iy = 0; iy < ny; iy++) {
  for (let ix = 0; ix < nx; ix++) {
   const east = x0 + ix * dx;
   const north = y0 + iy * dx;
   const p1 = destinationPoint(origin, 90, east);
   const p2 = destinationPoint(p1, 0, north);
   nodes.push({ id: nodes.length + 1, lat: p2[0], lon: p2[1] });
  }
 }
 _rayState.nodes = nodes;
 _rayState.results = [];
 _rayState.allResults = [];
 rayRedrawMapGraphics();
 rayUpdateSummary();
 rayRenderResultsTable();
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
   return { ok: false, reason: 'critical', offsetM: x, timeSec: t, path };
  }
  const theta = Math.asin(Math.min(0.999999, arg));
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
  const v = layers.length ? layers[layers.length - 1].v : 1500;
  const arg = p * v;
  if (arg >= 1) return { ok: false, reason: 'critical', offsetM: x, timeSec: t, path };
  const theta = Math.asin(Math.min(0.999999, arg));
  const dz = zr - z;
  const cosT = Math.cos(theta);
  x += dz * Math.tan(theta);
  t += dz / (v * cosT);
  path.push({ z: zr, x, v, theta: theta * 180 / Math.PI });
 }

 return { ok: true, offsetM: x, timeSec: t, path, p };
}

/** Exact straight-ray solution for a single constant velocity. */
function rayShootConstant(v, zs, zr, targetOffsetM) {
 const X = Math.abs(targetOffsetM);
 const D = zr - zs;
 if (!(D > 0) || !(v > 0)) return { ok: false, reason: 'bad_geometry' };
 const slant = Math.sqrt(X * X + D * D);
 const t = slant / v;
 const takeoffDeg = (Math.atan2(X, D) * 180) / Math.PI;
 const path = [
  { z: zs, x: 0, v, theta: takeoffDeg },
  { z: zr, x: X, v, theta: takeoffDeg }
 ];
 return { ok: true, offsetM: X, timeSec: t, path, takeoffDeg, p: Math.sin(takeoffDeg * Math.PI / 180) / v, method: 'exact' };
}

/** Shoot a ray from zs to hit horizontal offset X at depth zr. */
function rayShoot(layers, zs, zr, targetOffsetM) {
 const X = Math.abs(targetOffsetM);
 if (!(zr > zs)) return { ok: false, reason: 'receiver_above_source' };

 // Fast exact path for homogeneous water
 if (layers.length === 1 || (layers.length && layers.every(L => Math.abs(L.v - layers[0].v) < 1e-6))) {
  return rayShootConstant(layers[0].v, zs, zr, X);
 }

 if (X < 1) {
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
  return { ok: true, offsetM: 0, timeSec: t, path, takeoffDeg: 0, p: 0, method: 'vertical' };
 }

 const vmin = Math.min(...layers.map(L => L.v), 1500);
 let lo = 0, hi = (1 / vmin) * 0.999;
 let best = null;
 for (let iter = 0; iter < 64; iter++) {
  const mid = 0.5 * (lo + hi);
  const r = rayPropagate(mid, layers, zs, zr);
  if (!r.ok) { hi = mid; continue; }
  best = r;
  if (r.offsetM > X) hi = mid;
  else lo = mid;
  if (Math.abs(r.offsetM - X) < 0.25) break;
 }
 if (!best || !best.ok) return { ok: false, reason: 'no_solution' };

 const scale = best.offsetM > 1e-6 ? X / best.offsetM : 1;
 if (Math.abs(scale - 1) < 0.08) {
  best.path = best.path.map(pt => ({ ...pt, x: (pt.x || 0) * scale }));
  best.offsetM = X;
  // First-order TT correction for small geometric scale
  if (Math.abs(scale - 1) > 1e-6) best.timeSec = best.timeSec * (0.5 + 0.5 * scale);
 }
 const takeoff = best.path.find(pt => pt.theta != null);
 best.takeoffDeg = takeoff ? takeoff.theta : (Math.asin(Math.min(0.999, best.p * vmin)) * 180 / Math.PI);
 best.method = 'snell';
 return best;
}

function rayBuildResult(node, source, shot, brng) {
 const latlngs = shot.path.map(pt => {
  const d = Math.abs(pt.x || 0);
  if (d < 0.5) return source.slice();
  return destinationPoint(source, brng, d);
 });
 return {
  nodeId: node.id,
  nodeName: node.name || ('N' + node.id),
  offsetM: haversine(source, [node.lat, node.lon]),
  timeSec: shot.timeSec,
  takeoffDeg: shot.takeoffDeg,
  method: shot.method || 'snell',
  path: shot.path,
  latlngs,
  node: [node.lat, node.lon]
 };
}

function raySetBusy(busy, msg) {
 _rayState.busy = !!busy;
 const btn = document.getElementById('ray-btn-trace');
 if (btn) {
  btn.disabled = !!busy;
  btn.textContent = busy ? (msg || 'Tracing…') : 'Trace Rays';
  btn.style.opacity = busy ? '0.7' : '1';
 }
 const prog = document.getElementById('ray-progress');
 if (prog) {
  prog.style.display = busy ? 'block' : 'none';
  if (msg) prog.textContent = msg;
 }
}

async function rayTraceRun() {
 rayTraceStopPick();
 if (_rayState.busy) { showToast('Trace already running'); return; }
 if (!_rayState.source) { showToast('Place a source first'); return; }
 if (!_rayState.nodes.length) { showToast('Place, generate, or import at least one node'); return; }
 if (typeof haversine !== 'function' || typeof bearing !== 'function' || typeof destinationPoint !== 'function') {
  showToast('Map geometry helpers not ready — open Design workspace first', 5000);
  return;
 }

 const zs0 = Math.max(0, parseFloat(document.getElementById('ray-src-z')?.value) || 8);
 const zr0 = Math.max(zs0 + 1, parseFloat(document.getElementById('ray-rcv-z')?.value) || 1000);
 if (typeof velFieldAsk === 'function') {
  const ok = await velFieldAsk({
   title: 'Velocity field for ray tracing',
   coverZ: zr0,
   reason: 'Snell paths from source to nodes use this 1D V(z) field.'
  });
  if (!ok) { showToast('Ray trace cancelled — no velocity field', 3500); return; }
 } else if (rayGetVelMode() !== 'layered') {
  rayApplyVelocityMode(false);
 }

 const zs = Math.max(0, parseFloat(document.getElementById('ray-src-z')?.value) || 8);
 const zr = Math.max(zs + 1, parseFloat(document.getElementById('ray-rcv-z')?.value) || 1000);
 const maxOff = Math.max(100, parseFloat(document.getElementById('ray-max-off')?.value) || 8000);
 const maxDraw = Math.max(1, Math.min(2000, parseInt(document.getElementById('ray-max-draw')?.value, 10) || 200));
 let layers = velFieldGetLayers(zr);

 const nodes = _rayState.nodes.slice();
 const source = _rayState.source.slice();
 const token = ++_rayTraceToken;
 const results = [];
 const skipped = { maxOffset: 0, critical: 0, failed: 0 };
 const CHUNK = 40;
 let i = 0;

 raySetBusy(true, 'Tracing 0 / ' + nodes.length + '…');

 function finish() {
  if (token !== _rayTraceToken) return;
  results.sort((a, b) => a.offsetM - b.offsetM);
  _rayState.allResults = results;
  _rayState.results = results.slice(0, maxDraw);
  _rayState.skipped = skipped;
  _rayState.lastRunAt = new Date().toISOString();
  raySetBusy(false);
  rayRedrawMapGraphics();
  rayDrawProfile();
  rayUpdateSummary();
  rayRenderResultsTable();

  const parts = [];
  parts.push('Traced ' + results.length + ' ray(s)');
  if (results.length > maxDraw) parts.push('drawing ' + maxDraw);
  if (skipped.maxOffset) parts.push(skipped.maxOffset + ' beyond max offset');
  if (skipped.critical) parts.push(skipped.critical + ' critical / turning');
  if (skipped.failed) parts.push(skipped.failed + ' failed');
  showToast(parts.join(' · '), results.length ? 4000 : 6000);
  if (!results.length) {
   showToast('No rays reached nodes — check depths, max offset, or velocity model', 6000);
  }
 }

 function step() {
  if (token !== _rayTraceToken) return;
  const end = Math.min(i + CHUNK, nodes.length);
  for (; i < end; i++) {
   const node = nodes[i];
   const off = haversine(source, [node.lat, node.lon]);
   if (off > maxOff) { skipped.maxOffset++; continue; }
   const shot = rayShoot(layers, zs, zr, off);
   if (!shot.ok) {
    if (shot.reason === 'critical' || shot.reason === 'horizontal') skipped.critical++;
    else skipped.failed++;
    continue;
   }
   const brng = bearing(source, [node.lat, node.lon]);
   results.push(rayBuildResult(node, source, shot, brng));
  }
  raySetBusy(true, 'Tracing ' + i + ' / ' + nodes.length + '…');
  if (i < nodes.length) {
   setTimeout(step, 0);
  } else {
   finish();
  }
 }

 setTimeout(step, 0);
}

function rayTraceClear() {
 _rayTraceToken++;
 rayTraceStopPick();
 raySetBusy(false);
 _rayState.source = null;
 _rayState.nodes = [];
 _rayState.results = [];
 _rayState.allResults = [];
 _rayState.skipped = { maxOffset: 0, critical: 0, failed: 0 };
 if (layerRayTrace) layerRayTrace.clearLayers();
 rayUpdateSummary();
 rayRenderResultsTable();
 rayDrawProfile();
 showToast('Ray tracing cleared');
}

function rayFitMap() {
 if (!map || !layerRayTrace) return;
 const pts = [];
 if (_rayState.source) pts.push(_rayState.source);
 _rayState.nodes.forEach(n => pts.push([n.lat, n.lon]));
 if (pts.length < 1) return;
 try {
  map.fitBounds(L.latLngBounds(pts), { padding: [40, 40], maxZoom: 14 });
 } catch (_) {}
}

function rayTimeColor(t, tMin, tMax) {
 if (!(tMax > tMin)) return '#fbbf24';
 const u = Math.max(0, Math.min(1, (t - tMin) / (tMax - tMin)));
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
  }).bindTooltip((n.name || ('Node ' + n.id)), { permanent: false }).addTo(layerRayTrace);
 });

 const times = _rayState.results.map(r => r.timeSec);
 const tMin = times.length ? Math.min(...times) : 0;
 const tMax = times.length ? Math.max(...times) : 1;
 _rayState.results.forEach(r => {
  const col = rayTimeColor(r.timeSec, tMin, tMax);
  L.polyline(r.latlngs, {
   color: col, weight: 2, opacity: 0.85
  }).bindTooltip(
   (r.nodeName || ('N' + r.nodeId))
    + ' · ' + r.offsetM.toFixed(0) + ' m · '
    + r.timeSec.toFixed(3) + ' s · θ '
    + (r.takeoffDeg != null ? r.takeoffDeg.toFixed(1) : '—') + '°',
   { sticky: true }
  ).addTo(layerRayTrace);
 });
}

function rayUpdateSummary() {
 const el = document.getElementById('ray-summary');
 if (!el) return;
 const nSrc = _rayState.source ? 1 : 0;
 const nNodes = _rayState.nodes.length;
 const nRays = (_rayState.allResults.length || _rayState.results.length);
 const nDraw = _rayState.results.length;
 if (!nSrc && !nNodes) {
  el.textContent = 'No rays yet — place a source and nodes (or Import OBN / Generate patch), then Trace Rays.';
  return;
 }
 let html = `<strong style="color:#fbbf24;">${nSrc}</strong> source · <strong style="color:#38bdf8;">${nNodes}</strong> node(s) · <strong style="color:#30d158;">${nRays}</strong> ray(s)`
  + (nDraw < nRays ? ` <span style="color:#64748b;">(drawing ${nDraw})</span>` : '')
  + ` · vel <strong style="color:#fbbf24;">${_rayState.velMode || rayGetVelMode()}</strong>`;
 const sk = _rayState.skipped || {};
 if (sk.maxOffset || sk.critical || sk.failed) {
  html += `<br><span style="color:#f87171;">Skipped: ${sk.maxOffset || 0} max-offset · ${sk.critical || 0} critical · ${sk.failed || 0} failed</span>`;
 }
 if (nRays) {
  const pool = _rayState.allResults.length ? _rayState.allResults : _rayState.results;
  const times = pool.map(r => r.timeSec);
  const offs = pool.map(r => r.offsetM);
  html += `<br>Offset ${Math.min(...offs).toFixed(0)}–${Math.max(...offs).toFixed(0)} m · `
   + `TT ${(Math.min(...times)).toFixed(3)}–${(Math.max(...times)).toFixed(3)} s · `
   + `Takeoff ${Math.min(...pool.map(r => r.takeoffDeg)).toFixed(1)}–${Math.max(...pool.map(r => r.takeoffDeg)).toFixed(1)}° from vertical`;
 }
 el.innerHTML = html;
}

function rayRenderResultsTable() {
 const host = document.getElementById('ray-results-table');
 if (!host) return;
 const rows = _rayState.allResults.length ? _rayState.allResults : _rayState.results;
 if (!rows.length) {
  host.innerHTML = '<div style="color:#64748b;font-size:10px;padding:6px 0;">No travel-time table yet.</div>';
  return;
 }
 const show = rows.slice(0, 200);
 let html = '<table style="width:100%;border-collapse:collapse;font-size:10px;">'
  + '<thead><tr style="color:#94a3b8;text-align:left;">'
  + '<th style="padding:4px 6px;border-bottom:1px solid #1a1a24;">Node</th>'
  + '<th style="padding:4px 6px;border-bottom:1px solid #1a1a24;">Offset m</th>'
  + '<th style="padding:4px 6px;border-bottom:1px solid #1a1a24;">TT s</th>'
  + '<th style="padding:4px 6px;border-bottom:1px solid #1a1a24;">Takeoff°</th>'
  + '<th style="padding:4px 6px;border-bottom:1px solid #1a1a24;">Method</th>'
  + '</tr></thead><tbody>';
 show.forEach(r => {
  html += '<tr>'
   + `<td style="padding:3px 6px;border-bottom:1px solid #12121a;color:#e2e8f0;">${String(r.nodeName || r.nodeId).replace(/</g, '&lt;')}</td>`
   + `<td style="padding:3px 6px;border-bottom:1px solid #12121a;color:#cbd5e1;">${r.offsetM.toFixed(1)}</td>`
   + `<td style="padding:3px 6px;border-bottom:1px solid #12121a;color:#fbbf24;font-weight:700;">${r.timeSec.toFixed(4)}</td>`
   + `<td style="padding:3px 6px;border-bottom:1px solid #12121a;color:#94a3b8;">${r.takeoffDeg != null ? r.takeoffDeg.toFixed(2) : '—'}</td>`
   + `<td style="padding:3px 6px;border-bottom:1px solid #12121a;color:#64748b;">${r.method || 'snell'}</td>`
   + '</tr>';
 });
 html += '</tbody></table>';
 if (rows.length > show.length) {
  html += `<div style="font-size:9px;color:#64748b;margin-top:6px;">Showing ${show.length} of ${rows.length} — export CSV for full table.</div>`;
 }
 host.innerHTML = html;
}

function rayExportCsv() {
 const rows = _rayState.allResults.length ? _rayState.allResults : _rayState.results;
 if (!rows.length) { showToast('No results to export — run Trace Rays first'); return; }
 const zs = parseFloat(document.getElementById('ray-src-z')?.value) || 8;
 const zr = parseFloat(document.getElementById('ray-rcv-z')?.value) || 1000;
 const lines = [
  '# Candooka OSPO water-column ray tracing',
  '# velMode=' + (_rayState.velMode || ''),
  '# sourceDepth_m=' + zs + ' nodeDepth_m=' + zr,
  '# source_lat=' + (_rayState.source ? _rayState.source[0] : '') + ' source_lon=' + (_rayState.source ? _rayState.source[1] : ''),
  'node_id,node_name,node_lat,node_lon,offset_m,travel_time_s,takeoff_deg,method'
 ];
 rows.forEach(r => {
  lines.push([
   r.nodeId,
   JSON.stringify(String(r.nodeName || '')),
   r.node[0],
   r.node[1],
   r.offsetM.toFixed(3),
   r.timeSec.toFixed(6),
   r.takeoffDeg != null ? r.takeoffDeg.toFixed(4) : '',
   r.method || ''
  ].join(','));
 });
 const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
 const a = document.createElement('a');
 a.href = URL.createObjectURL(blob);
 a.download = 'ray_tracing_tt_' + new Date().toISOString().slice(0, 10) + '.csv';
 a.click();
 URL.revokeObjectURL(a.href);
 showToast('Exported ' + rows.length + ' travel times', 2500);
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

 ctx.strokeStyle = '#334155';
 ctx.setLineDash([4, 3]);
 ctx.beginPath(); ctx.moveTo(padL, zToPx(zr)); ctx.lineTo(W - padR, zToPx(zr)); ctx.stroke();
 ctx.setLineDash([]);

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

 ctx.fillStyle = '#f59e0b';
 ctx.beginPath();
 ctx.arc(xToPx(0), zToPx(zs), 4, 0, Math.PI * 2);
 ctx.fill();
}
