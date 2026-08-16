#!/usr/bin/env node
/**
 * Candooka coastal AIS daemon
 * Primary:  AISHub HTTP poll (AISHUB_USERNAME — https://www.aishub.net/api)
 * Optional: AISStream WebSocket if AISSTREAM_API_KEY is set (often down)
 *
 * Config: /etc/candooka/ais.env
 *   AISHUB_USERNAME=...      (required for live AIS)
 *   AISSTREAM_API_KEY=...    (optional secondary)
 */
const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');
const WebSocket = require('ws');

const DATA_DIR = '/var/www/candooka/data';
const LIVE_FILE = path.join(DATA_DIR, 'ais-live.json');
const WANTED_FILE = path.join(DATA_DIR, 'ais-wanted.json');
const BBOX_FILE = path.join(DATA_DIR, 'ais-bbox.json');
const SEISMIC_ON_FILE = path.join(DATA_DIR, 'ais-seismic-on.json');
const STATUS_FILE = path.join(DATA_DIR, 'ais-status.json');
const ENV_FILE = '/etc/candooka/ais.env';
const FLEET_FILE = path.join(__dirname, 'seismic-fleet.json');
const WS_URL = 'wss://stream.aisstream.io/v0/stream';
const AISHUB_URL = 'https://data.aishub.net/ws.php';

const positions = new Map();
let seismicFleet = new Map(); // mmsi -> meta
let ws = null;
let lastSubKey = '';
let reconnectTimer = null;
let lastStreamMsgAt = 0;
let activeSource = 'none'; // aisstream | aishub | none
let hubTimer = null;

/** Name patterns for dedicated marine seismic acquisition vessels. */
const SEISMIC_NAME_RE = /\b(RAMFORM|GEO\s?(CARIBBEAN|CORAL|CASPIAN|CELTIC|PACIFIC)|OCEANIC\s?(SIRIUS|VEGA|ENDEAVOUR|CHAMPION)|AMAZON\s?(WARRIOR|CONQUEROR)|SW\s?(EMPRESS|DUKE|DUCHESS|GALLIEN|TASMAN|BLY|BARET|MIKKELSEN|AMUNDSEN|COLUMBUS|MAGELLAN|VESPUCCI|COOK|THURIDUR)|BGP\s?(PROSPECTOR|CHALLENGER|EXPLORER|PIONEER)|SANCO\s?(SWIFT|SWORD)|POLARCUS|GEOWAVE|HAI YANG SHI YOU\s?7|VYACHESLAV TIKHONOV|VOYAGER EXPLORER|OSPREY EXPLORER|HARRIER EXPLORER|SEABIRD EXPLORER)\b/i;

function loadSeismicFleet() {
  seismicFleet = new Map();
  try {
    const raw = JSON.parse(fs.readFileSync(FLEET_FILE, 'utf8'));
    const list = Array.isArray(raw) ? raw : (raw.vessels || []);
    for (const v of list) {
      const mmsi = String(v.mmsi || '').replace(/\D/g, '');
      if (mmsi.length === 9) seismicFleet.set(mmsi, v);
    }
  } catch (e) {
    console.error('[ais] seismic fleet load failed', e.message);
  }
  console.log('[ais] seismic fleet roster:', seismicFleet.size);
}

function seismicModeOn() {
  const b = readJson(SEISMIC_ON_FILE, null);
  if (!b || !b.on) return false;
  // Keep warm for 30 min after last UI ping
  if (Date.now() - Number(b.at || 0) > 30 * 60 * 1000) return false;
  return true;
}

function seismicMmsis() {
  return [...seismicFleet.keys()];
}

function isSeismicName(name) {
  return !!(name && SEISMIC_NAME_RE.test(String(name)));
}

function loadEnv() {
  const env = {};
  try {
    for (const raw of fs.readFileSync(ENV_FILE, 'utf8').split(/\r?\n/)) {
      const line = raw.trim();
      if (!line || line.startsWith('#')) continue;
      const i = line.indexOf('=');
      if (i < 0) continue;
      env[line.slice(0, i).trim()] = line.slice(i + 1).trim().replace(/^["']|["']$/g, '');
    }
  } catch (_) {}
  return env;
}

function hasStreamKey(env) {
  const apiKey = env.AISSTREAM_API_KEY || process.env.AISSTREAM_API_KEY || '';
  return !!(apiKey && apiKey.length >= 8 && !/your_|changeme|xxx/i.test(apiKey));
}

function hubUser(env) {
  const u = env.AISHUB_USERNAME || process.env.AISHUB_USERNAME || '';
  return (u && u.length >= 2 && !/your_|changeme|xxx/i.test(u)) ? u : '';
}

function ensureDataDir() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

function writeStatus(partial) {
  ensureDataDir();
  let prev = {};
  try { prev = JSON.parse(fs.readFileSync(STATUS_FILE, 'utf8')); } catch (_) {}
  fs.writeFileSync(STATUS_FILE, JSON.stringify({
    ...prev,
    ...partial,
    source: partial.source != null ? partial.source : (partial.activeSource || activeSource),
    activeSource,
    updatedAt: new Date().toISOString(),
    vesselCount: positions.size,
  }, null, 2));
}

function writeLive() {
  ensureDataDir();
  const obj = {};
  for (const [mmsi, rec] of positions) obj[mmsi] = rec;
  fs.writeFileSync(LIVE_FILE, JSON.stringify(obj));
}

function readJson(file, fallback) {
  try {
    if (!fs.existsSync(file)) return fallback;
    return JSON.parse(fs.readFileSync(file, 'utf8')) || fallback;
  } catch (_) {
    return fallback;
  }
}

function wantedMmsis() {
  const list = readJson(WANTED_FILE, {});
  const now = Date.now() / 1000;
  const out = [];
  for (const [mmsi, seen] of Object.entries(list)) {
    if (Number(seen) > now - 3600 && /^\d{9}$/.test(mmsi)) out.push(mmsi);
  }
  return out;
}

function wantedBbox() {
  const b = readJson(BBOX_FILE, null);
  if (!b) return null;
  if (Date.now() - Number(b.at || 0) > 5 * 60 * 1000) return null;
  const { minlat, minlon, maxlat, maxlon } = b;
  if (![minlat, minlon, maxlat, maxlon].every(Number.isFinite)) return null;
  if (maxlat - minlat > 20 || maxlon - minlon > 20) return null;
  return { minlat, minlon, maxlat, maxlon };
}

function defaultBbox() {
  return { minlat: -2, minlon: 100, maxlat: 8, maxlon: 110 };
}

function buildSubscription(apiKey) {
  const seismic = seismicModeOn();
  // Global box when tracking the seismic fleet; otherwise map-view / default SE Asia box
  const bbox = seismic
    ? { minlat: -80, minlon: -180, maxlat: 80, maxlon: 180 }
    : (wantedBbox() || defaultBbox());
  const mmsiSet = new Set(wantedMmsis());
  if (seismic) {
    for (const m of seismicMmsis()) mmsiSet.add(m);
  }
  const mmsi = [...mmsiSet].slice(0, 50);
  const sub = {
    APIKey: apiKey,
    BoundingBoxes: [[[bbox.minlat, bbox.minlon], [bbox.maxlat, bbox.maxlon]]],
    FilterMessageTypes: ['PositionReport', 'StandardClassBPositionReport', 'ExtendedClassBPositionReport', 'ShipStaticData'],
  };
  // MMSI filter when we have a roster / track list (keeps global stream tractable)
  if (mmsi.length) sub.FiltersShipMMSI = mmsi;
  return { sub, key: JSON.stringify({ bbox, mmsi, seismic }), bbox, mmsi, seismic };
}

function upsertVessel(rec) {
  if (!rec || !rec.mmsi) return;
  const mmsi = String(rec.mmsi).replace(/\D/g, '');
  if (mmsi.length !== 9) return;
  if (typeof rec.lat !== 'number' || typeof rec.lon !== 'number') return;
  if (!Number.isFinite(rec.lat) || !Number.isFinite(rec.lon)) return;
  const prev = positions.get(mmsi) || { mmsi };
  const name = rec.name || prev.name || null;
  const roster = seismicFleet.get(mmsi);
  const seismic = !!(roster || prev.seismic || isSeismicName(name));
  positions.set(mmsi, {
    mmsi,
    lat: rec.lat,
    lon: rec.lon,
    sog: typeof rec.sog === 'number' ? rec.sog : (prev.sog ?? null),
    cog: typeof rec.cog === 'number' ? rec.cog : (prev.cog ?? null),
    heading: typeof rec.heading === 'number' ? rec.heading : (prev.heading ?? null),
    name: name || (roster && roster.name) || null,
    operator: (roster && roster.operator) || prev.operator || null,
    imo: (roster && roster.imo) || prev.imo || null,
    seismic,
    timestamp: rec.timestamp || new Date().toISOString(),
    source: rec.source || prev.source || 'unknown',
  });
}

function upsertFromMessage(msg) {
  const type = msg.MessageType;
  const meta = msg.MetaData || {};
  const body = (msg.Message && (msg.Message[type] || msg.Message.PositionReport || msg.Message.StandardClassBPositionReport)) || {};
  const mmsi = String(meta.MMSI || body.UserID || '').replace(/\D/g, '');
  if (mmsi.length !== 9) return;

  const lat = meta.latitude;
  const lon = meta.longitude;
  if (typeof lat !== 'number' || typeof lon !== 'number') return;

  const prev = positions.get(mmsi) || { mmsi };
  let sog = prev.sog, cog = prev.cog, heading = prev.heading;
  let name = prev.name || String(meta.ShipName || '').trim() || null;
  if (typeof body.Sog === 'number') sog = body.Sog;
  if (typeof body.Cog === 'number') cog = body.Cog;
  if (typeof body.TrueHeading === 'number' && body.TrueHeading !== 511) heading = body.TrueHeading;
  else if (typeof cog === 'number') heading = cog;
  if (type === 'ShipStaticData' && body.Name) name = String(body.Name).trim();

  upsertVessel({
    mmsi, lat, lon, sog, cog, heading, name,
    timestamp: meta.time_utc || new Date().toISOString(),
    source: 'aisstream',
  });
  lastStreamMsgAt = Date.now();
  activeSource = 'aisstream';
}

function scheduleReconnect(ms) {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connect, ms);
}

function httpGetJson(url, timeoutMs = 20000) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith('https') ? https : http;
    const req = lib.get(url, { headers: { 'User-Agent': 'CandookaOSPO/1.0', Accept: 'application/json' } }, (res) => {
      if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        res.resume();
        return httpGetJson(res.headers.location, timeoutMs).then(resolve, reject);
      }
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        const raw = Buffer.concat(chunks).toString('utf8');
        if (res.statusCode < 200 || res.statusCode >= 300) {
          reject(new Error('HTTP ' + res.statusCode + ': ' + raw.slice(0, 120)));
          return;
        }
        try { resolve(JSON.parse(raw)); }
        catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.setTimeout(timeoutMs, () => { req.destroy(new Error('timeout')); });
  });
}

/** AISHub human-readable JSON: either [{...}] or [ [meta], [rows...] ]. */
function parseAisHubPayload(data) {
  if (!data) return [];
  let rows = data;
  if (Array.isArray(data) && data.length >= 2 && Array.isArray(data[1])) {
    rows = data[1];
  }
  if (!Array.isArray(rows)) return [];
  const out = [];
  for (const r of rows) {
    if (!r || typeof r !== 'object') continue;
    const mmsi = String(r.MMSI || r.mmsi || '').replace(/\D/g, '');
    let lat = r.LATITUDE != null ? Number(r.LATITUDE) : Number(r.lat);
    let lon = r.LONGITUDE != null ? Number(r.LONGITUDE) : Number(r.lon);
    // Some AISHub formats use 1/600000 deg
    if (Number.isFinite(lat) && Math.abs(lat) > 90) lat = lat / 600000;
    if (Number.isFinite(lon) && Math.abs(lon) > 180) lon = lon / 600000;
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    let sog = r.SOG != null ? Number(r.SOG) : null;
    let cog = r.COG != null ? Number(r.COG) : null;
    let heading = r.HEADING != null ? Number(r.HEADING) : null;
    if (sog != null && sog > 100) sog = sog / 10;
    if (cog != null && cog > 360) cog = cog / 10;
    if (heading === 511) heading = null;
    const name = (r.NAME || r.name || '').toString().trim() || null;
    const t = r.TIME || r.time;
    let timestamp = new Date().toISOString();
    if (typeof t === 'string' && t.includes('-')) timestamp = new Date(t).toISOString();
    else if (t && Number(t) > 1e9) timestamp = new Date(Number(t) * (Number(t) > 1e12 ? 1 : 1000)).toISOString();
    out.push({ mmsi, lat, lon, sog, cog, heading, name, timestamp, source: 'aishub' });
  }
  return out;
}

async function pollAisHub() {
  const env = loadEnv();
  const user = hubUser(env);
  if (!user) return false;

  // AISHub is primary. Only skip a poll if AISStream is freshly delivering.
  const streamFresh = hasStreamKey(env) && ws && ws.readyState === WebSocket.OPEN
    && (Date.now() - lastStreamMsgAt) < 45 * 1000 && lastStreamMsgAt > 0;
  if (streamFresh && positions.size > 0 && !seismicModeOn()) return false;

  const bbox = seismicModeOn()
    ? { minlat: -80, minlon: -180, maxlat: 80, maxlon: 180 }
    : (wantedBbox() || defaultBbox());
  const mmsiList = wantedMmsis();
  if (seismicModeOn()) {
    for (const m of seismicMmsis()) {
      if (!mmsiList.includes(m)) mmsiList.push(m);
    }
  }
  const params = new URLSearchParams({
    username: user,
    format: '1',
    output: 'json',
    compress: '0',
    latmin: String(bbox.minlat),
    latmax: String(bbox.maxlat),
    lonmin: String(bbox.minlon),
    lonmax: String(bbox.maxlon),
    interval: '180',
  });
  // AISHub accepts comma-separated MMSIs — prefer roster when in seismic mode
  if (seismicModeOn() && mmsiList.length) {
    params.set('mmsi', mmsiList.slice(0, 40).join(','));
  } else if (mmsiList.length === 1) {
    params.set('mmsi', mmsiList[0]);
  }

  try {
    const data = await httpGetJson(AISHUB_URL + '?' + params.toString());
    const vessels = parseAisHubPayload(data);
    let n = 0;
    for (const v of vessels) {
      upsertVessel(v);
      n++;
    }
    if (n > 0) {
      activeSource = 'aishub';
      writeStatus({
        ok: true,
        configured: true,
        error: null,
        primary: 'aishub',
        hubVessels: n,
        bbox,
      });
      writeLive();
      console.log('[ais] AISHub:', n, 'vessels');
    } else {
      writeStatus({
        ok: false,
        configured: true,
        primary: 'aishub',
        error: 'AISHub returned 0 vessels for current view/roster',
        hubVessels: 0,
        bbox,
      });
    }
    return n > 0;
  } catch (e) {
    console.error('[ais] AISHub error', e.message);
    writeStatus({
      ok: false,
      configured: true,
      primary: 'aishub',
      error: 'AISHub: ' + e.message,
    });
    return false;
  }
}

function connect() {
  const env = loadEnv();
  const hub = hubUser(env);

  // AISHub is the configured primary source
  if (!hub) {
    writeStatus({
      ok: false,
      configured: false,
      primary: 'aishub',
      error: 'Missing AISHUB_USERNAME in /etc/candooka/ais.env — join https://www.aishub.net and share a terrestrial AIS feed to get a username',
      activeSource: 'none',
    });
    activeSource = 'none';
    console.error('[ais] No AISHUB_USERNAME — join https://www.aishub.net');
    scheduleReconnect(60000);
    return;
  }

  activeSource = 'aishub';
  writeStatus({
    ok: false,
    configured: true,
    primary: 'aishub',
    error: 'AISHub configured — waiting for first poll',
  });
  console.log('[ais] AISHub primary enabled for user', hub.slice(0, 2) + '…');

  // Optional secondary: AISStream (often unavailable)
  if (!hasStreamKey(env)) {
    return;
  }

  const apiKey = env.AISSTREAM_API_KEY || process.env.AISSTREAM_API_KEY || '';
  if (ws) { try { ws.terminate(); } catch (_) {} ws = null; }

  console.log('[ais] also connecting optional AISStream…');
  ws = new WebSocket(WS_URL);
  const connectTimeout = setTimeout(() => { try { ws.terminate(); } catch (_) {} }, 8000);

  ws.on('open', () => {
    const { sub, key, bbox, mmsi } = buildSubscription(apiKey);
    lastSubKey = key;
    ws.send(JSON.stringify(sub));
    clearTimeout(connectTimeout);
    activeSource = 'aisstream';
    writeStatus({ ok: true, configured: true, error: null, bbox, trackedMmsi: mmsi, primary: 'aishub', secondary: 'aisstream' });
    console.log('[ais] AISStream subscribed', JSON.stringify(bbox), 'mmsi', mmsi.length);
  });

  ws.on('message', (raw) => {
    try {
      const msg = JSON.parse(raw.toString());
      if (msg.error || msg.Error) {
        writeStatus({ ok: !!hub, configured: true, error: 'AISStream: ' + String(msg.error || msg.Error), primary: 'aishub' });
        return;
      }
      upsertFromMessage(msg);
    } catch (_) {}
  });

  ws.on('error', (err) => {
    clearTimeout(connectTimeout);
    console.error('[ais] AISStream error', err.message);
  });

  ws.on('close', () => {
    clearTimeout(connectTimeout);
    scheduleReconnect(15000);
  });
}

function maybeResubscribe() {
  const env = loadEnv();
  if (!hasStreamKey(env) || !ws || ws.readyState !== WebSocket.OPEN) return;
  const apiKey = env.AISSTREAM_API_KEY || process.env.AISSTREAM_API_KEY || '';
  const { sub, key } = buildSubscription(apiKey);
  if (key === lastSubKey) return;
  lastSubKey = key;
  try {
    ws.send(JSON.stringify(sub));
    writeStatus({ ok: true, configured: true, error: null, resubscribedAt: new Date().toISOString() });
    console.log('[ais] resubscribed');
  } catch (e) {
    console.error('[ais] resubscribe failed', e.message);
  }
}

setInterval(() => {
  const cutoff = Date.now() - 30 * 60 * 1000;
  for (const [mmsi, rec] of positions) {
    const t = Date.parse(rec.timestamp || 0);
    if (Number.isFinite(t) && t < cutoff) positions.delete(mmsi);
  }
  writeLive();
  maybeResubscribe();
}, 10000);

// AISHub poll every 25s (primary feed)
hubTimer = setInterval(() => {
  pollAisHub().catch(() => {});
}, 25000);

ensureDataDir();
loadSeismicFleet();
writeLive();
connect();
setTimeout(() => { pollAisHub().catch(() => {}); }, 1500);
console.log('[ais] daemon started (AISHub primary, optional AISStream, seismic fleet roster)');
