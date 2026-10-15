#!/usr/bin/env node
/**
 * Candooka coastal AIS daemon
 * Free feeds (no transceiver):
 *   1. Digitraffic Finland — Baltic / Finnish waters (HTTP)
 *   2. Kystverket Norway open AIS — Norwegian EEZ / Svalbard (TCP NMEA)
 * Optional: AISHub / AISStream if credentials exist
 *
 * Config: /etc/candooka/ais.env (optional keys only)
 */
const fs = require('fs');
const path = require('path');
const net = require('net');
const https = require('https');
const http = require('http');
const zlib = require('zlib');
const WebSocket = require('ws');
const { AisDecode } = require('ais-decoder');

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
const DIGITRAFFIC_LOC = 'https://meri.digitraffic.fi/api/ais/v1/locations';
const DIGITRAFFIC_VES = 'https://meri.digitraffic.fi/api/ais/v1/vessels';
const NORWAY_AIS_HOST = '153.44.253.27';
const NORWAY_AIS_PORT = 5631;

const positions = new Map();
const vesselMeta = new Map(); // mmsi -> { name, imo, shipType }
let seismicFleet = new Map();
let ws = null;
let lastSubKey = '';
let reconnectTimer = null;
let lastStreamMsgAt = 0;
let activeSource = 'none';
let hubTimer = null;
let digitrafficTimer = null;
let norwaySocket = null;
let norwayReconnectTimer = null;
let norwayBuf = '';
let norwayMsgCount = 0;
let norwayUpsertCount = 0;
let norwayLastAt = 0;
const aisSessions = {}; // multipart reassembly

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
  // Digitraffic coverage is Baltic / Finnish waters — default near Helsinki
  return { minlat: 59.0, minlon: 21.0, maxlat: 61.5, maxlon: 28.5 };
}

function norwayDefaultBbox() {
  // Norwegian EEZ / coast + Svalbard approaches
  return { minlat: 57.0, minlon: 4.0, maxlat: 72.0, maxlon: 32.0 };
}

function interestBboxes() {
  const b = wantedBbox();
  if (b) return [b];
  return [defaultBbox(), norwayDefaultBbox()];
}

function inAnyBbox(lat, lon, boxes) {
  for (const b of boxes) {
    if (lat >= b.minlat && lat <= b.maxlat && lon >= b.minlon && lon <= b.maxlon) return true;
  }
  return false;
}

function shouldKeepVessel(mmsi, lat, lon) {
  if (seismicFleet.has(mmsi)) return true;
  if (wantedMmsis().includes(mmsi)) return true;
  if (seismicModeOn()) return seismicFleet.has(mmsi); // roster only when seismic watch
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
  return inAnyBbox(lat, lon, interestBboxes());
}

function buildSubscription(apiKey) {
  const seismic = seismicModeOn();
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
  const meta = vesselMeta.get(mmsi) || {};
  const name = rec.name || prev.name || meta.name || null;
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
    imo: (roster && roster.imo) || prev.imo || meta.imo || null,
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
  reconnectTimer = setTimeout(connectOptionalStream, ms);
}

function httpGetJson(url, timeoutMs = 25000) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith('https') ? https : http;
    const req = lib.get(url, {
      headers: {
        'User-Agent': 'CandookaOSPO/1.0 (admin@candooka.world)',
        Accept: 'application/json',
        'Accept-Encoding': 'gzip',
      },
    }, (res) => {
      if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        res.resume();
        return httpGetJson(res.headers.location, timeoutMs).then(resolve, reject);
      }
      const enc = (res.headers['content-encoding'] || '').toLowerCase();
      const stream = enc.includes('gzip') ? res.pipe(zlib.createGunzip()) : res;
      const chunks = [];
      stream.on('data', (c) => chunks.push(c));
      stream.on('error', reject);
      stream.on('end', () => {
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

function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const toR = Math.PI / 180;
  const dLat = (lat2 - lat1) * toR;
  const dLon = (lon2 - lon1) * toR;
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1 * toR) * Math.cos(lat2 * toR) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

async function refreshDigitrafficMeta() {
  try {
    const list = await httpGetJson(DIGITRAFFIC_VES);
    if (!Array.isArray(list)) return;
    for (const v of list) {
      const mmsi = String(v.mmsi || '').replace(/\D/g, '');
      if (mmsi.length !== 9) continue;
      vesselMeta.set(mmsi, {
        name: (v.name || '').toString().trim() || null,
        imo: v.imo || null,
        shipType: v.shipType || null,
      });
    }
    console.log('[ais] Digitraffic vessel meta:', vesselMeta.size);
  } catch (e) {
    console.error('[ais] Digitraffic meta error', e.message);
  }
}

async function pollDigitraffic() {
  const bbox = wantedBbox() || defaultBbox();
  const seismic = seismicModeOn();
  const wanted = new Set(wantedMmsis());
  if (seismic) for (const m of seismicMmsis()) wanted.add(m);

  const clat = (bbox.minlat + bbox.maxlat) / 2;
  const clon = (bbox.minlon + bbox.maxlon) / 2;
  const cornerKm = haversineKm(clat, clon, bbox.maxlat, bbox.maxlon);
  const radius = Math.min(200, Math.max(30, Math.ceil(cornerKm * 1.15)));

  try {
    // Radius query for map view; also full dump when seismic/wanted (filter client-side)
    let url = DIGITRAFFIC_LOC + '?latitude=' + clat.toFixed(4)
      + '&longitude=' + clon.toFixed(4)
      + '&radius=' + radius;
    if (wanted.size === 1) {
      url = DIGITRAFFIC_LOC + '?mmsi=' + [...wanted][0];
    }
    const data = await httpGetJson(url);
    const feats = (data && data.features) || [];
    let n = 0;
    for (const f of feats) {
      const mmsi = String(f.mmsi || (f.properties && f.properties.mmsi) || '').replace(/\D/g, '');
      if (mmsi.length !== 9) continue;
      const coords = f.geometry && f.geometry.coordinates;
      if (!coords || coords.length < 2) continue;
      const lon = Number(coords[0]);
      const lat = Number(coords[1]);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;

      // Always keep wanted/seismic; otherwise keep if inside bbox
      const inWanted = wanted.has(mmsi);
      const inBox = lat >= bbox.minlat && lat <= bbox.maxlat && lon >= bbox.minlon && lon <= bbox.maxlon;
      if (!inWanted && !inBox && !seismic) continue;
      if (seismic && !inWanted && !isSeismicName((vesselMeta.get(mmsi) || {}).name)) {
        // when seismic mode, also keep name matches from Digitraffic dump
        if (!inBox) continue;
      }

      const p = f.properties || {};
      let heading = typeof p.heading === 'number' ? p.heading : null;
      if (heading === 511) heading = null;
      const tsExt = p.timestampExternal ? Number(p.timestampExternal) : null;
      const timestamp = tsExt && tsExt > 1e12
        ? new Date(tsExt).toISOString()
        : (tsExt ? new Date(tsExt * 1000).toISOString() : new Date().toISOString());
      upsertVessel({
        mmsi,
        lat,
        lon,
        sog: typeof p.sog === 'number' ? p.sog : null,
        cog: typeof p.cog === 'number' ? p.cog : null,
        heading,
        name: (vesselMeta.get(mmsi) || {}).name || null,
        timestamp,
        source: 'digitraffic',
      });
      n++;
    }

    // If seismic mode, also pull full locations once and filter roster (Baltic-only hits)
    if (seismic && wanted.size > 1) {
      try {
        const all = await httpGetJson(DIGITRAFFIC_LOC);
        for (const f of (all.features || [])) {
          const mmsi = String(f.mmsi || (f.properties && f.properties.mmsi) || '').replace(/\D/g, '');
          if (!wanted.has(mmsi)) continue;
          const coords = f.geometry && f.geometry.coordinates;
          if (!coords) continue;
          const lon = Number(coords[0]);
          const lat = Number(coords[1]);
          const p = f.properties || {};
          let heading = typeof p.heading === 'number' ? p.heading : null;
          if (heading === 511) heading = null;
          const tsExt = p.timestampExternal ? Number(p.timestampExternal) : null;
          const timestamp = tsExt && tsExt > 1e12
            ? new Date(tsExt).toISOString()
            : new Date().toISOString();
          upsertVessel({
            mmsi, lat, lon,
            sog: typeof p.sog === 'number' ? p.sog : null,
            cog: typeof p.cog === 'number' ? p.cog : null,
            heading,
            name: (vesselMeta.get(mmsi) || {}).name || (seismicFleet.get(mmsi) || {}).name || null,
            timestamp,
            source: 'digitraffic',
          });
          n++;
        }
      } catch (_) {}
    }

    activeSource = activeSource === 'norway' ? 'norway' : 'digitraffic';
    writeStatus({
      ok: true,
      configured: true,
      primary: 'digitraffic+norway',
      error: null,
      digitrafficVessels: n,
      bbox,
      coverage: 'Digitraffic (Finnish/Baltic) + Kystverket Norway open AIS — no transceiver',
      norwayConnected: !!(norwaySocket && !norwaySocket.destroyed),
    });
    writeLive();
    if (n > 0) console.log('[ais] Digitraffic:', n, 'vessels');
    return n > 0;
  } catch (e) {
    console.error('[ais] Digitraffic error', e.message);
    writeStatus({
      ok: false,
      configured: true,
      primary: 'digitraffic',
      error: 'Digitraffic: ' + e.message,
    });
    return false;
  }
}

function parseAisHubPayload(data) {
  if (!data) return [];
  let rows = data;
  if (Array.isArray(data) && data.length >= 2 && Array.isArray(data[1])) rows = data[1];
  if (!Array.isArray(rows)) return [];
  const out = [];
  for (const r of rows) {
    if (!r || typeof r !== 'object') continue;
    const mmsi = String(r.MMSI || r.mmsi || '').replace(/\D/g, '');
    let lat = r.LATITUDE != null ? Number(r.LATITUDE) : Number(r.lat);
    let lon = r.LONGITUDE != null ? Number(r.LONGITUDE) : Number(r.lon);
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
  if (seismicModeOn() && mmsiList.length) params.set('mmsi', mmsiList.slice(0, 40).join(','));
  else if (mmsiList.length === 1) params.set('mmsi', mmsiList[0]);

  try {
    const data = await httpGetJson(AISHUB_URL + '?' + params.toString());
    const vessels = parseAisHubPayload(data);
    let n = 0;
    for (const v of vessels) { upsertVessel(v); n++; }
    if (n > 0) {
      activeSource = 'aishub';
      writeStatus({ ok: true, configured: true, error: null, hubVessels: n, bbox });
      writeLive();
      console.log('[ais] AISHub optional:', n, 'vessels');
    }
    return n > 0;
  } catch (e) {
    console.error('[ais] AISHub error', e.message);
    return false;
  }
}

function connectOptionalStream() {
  const env = loadEnv();
  if (!hasStreamKey(env)) return;
  const apiKey = env.AISSTREAM_API_KEY || process.env.AISSTREAM_API_KEY || '';
  if (ws) { try { ws.terminate(); } catch (_) {} ws = null; }

  console.log('[ais] optional AISStream connecting…');
  ws = new WebSocket(WS_URL);
  const connectTimeout = setTimeout(() => { try { ws.terminate(); } catch (_) {} }, 8000);

  ws.on('open', () => {
    const { sub, key, bbox, mmsi } = buildSubscription(apiKey);
    lastSubKey = key;
    ws.send(JSON.stringify(sub));
    clearTimeout(connectTimeout);
    console.log('[ais] AISStream subscribed', JSON.stringify(bbox), 'mmsi', mmsi.length);
  });
  ws.on('message', (raw) => {
    try {
      const msg = JSON.parse(raw.toString());
      if (msg.error || msg.Error) return;
      upsertFromMessage(msg);
    } catch (_) {}
  });
  ws.on('error', (err) => {
    clearTimeout(connectTimeout);
    console.error('[ais] AISStream error', err.message);
  });
  ws.on('close', () => {
    clearTimeout(connectTimeout);
    scheduleReconnect(30000);
  });
}

function maybeResubscribe() {
  const env = loadEnv();
  if (!hasStreamKey(env) || !ws || ws.readyState !== WebSocket.OPEN) return;
  const apiKey = env.AISSTREAM_API_KEY || process.env.AISSTREAM_API_KEY || '';
  const { sub, key } = buildSubscription(apiKey);
  if (key === lastSubKey) return;
  lastSubKey = key;
  try { ws.send(JSON.stringify(sub)); } catch (_) {}
}

/** Normalize Kystverket talkers (!BSVDM / !B1VDM) to !AIVDM and strip \s:… tags. */
function normalizeNmeaLine(raw) {
  let s = String(raw || '').trim();
  if (!s) return null;
  const bang = s.lastIndexOf('!');
  if (bang >= 0) s = s.slice(bang);
  s = s.replace(/^![A-Z0-9]{2}VDM/, '!AIVDM').replace(/^![A-Z0-9]{2}VDO/, '!AIVDO');
  if (!s.startsWith('!AIVDM') && !s.startsWith('!AIVDO')) return null;
  return s;
}

function handleNorwayNmea(line) {
  const nmea = normalizeNmeaLine(line);
  if (!nmea) return;
  norwayMsgCount++;
  let dec;
  try {
    dec = new AisDecode(nmea, aisSessions);
  } catch (_) {
    return;
  }
  if (!dec || !dec.mmsi) return;

  const mmsi = String(dec.mmsi).replace(/\D/g, '');
  if (mmsi.length !== 9) return;

  // Type 5 static data — store name for later position reports
  if (dec.aistype === 5 && dec.shipname) {
    const name = String(dec.shipname).replace(/@+$/g, '').trim();
    if (name) {
      const prev = vesselMeta.get(mmsi) || {};
      vesselMeta.set(mmsi, { ...prev, name, imo: dec.imo || prev.imo || null });
      const pos = positions.get(mmsi);
      if (pos) {
        pos.name = pos.name || name;
        positions.set(mmsi, pos);
      }
    }
    return;
  }

  const lat = typeof dec.lat === 'number' ? dec.lat : null;
  const lon = typeof dec.lon === 'number' ? dec.lon : null;
  if (lat == null || lon == null || !Number.isFinite(lat) || !Number.isFinite(lon)) return;
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return;
  if (!shouldKeepVessel(mmsi, lat, lon)) return;

  let sog = typeof dec.sog === 'number' ? dec.sog : null;
  let cog = typeof dec.cog === 'number' ? dec.cog : null;
  let heading = typeof dec.hdg === 'number' ? dec.hdg : (typeof dec.heading === 'number' ? dec.heading : null);
  if (heading === 511) heading = null;
  if (cog != null && cog > 360) cog = null;
  if (sog != null && sog > 100) sog = null;

  const meta = vesselMeta.get(mmsi) || {};
  upsertVessel({
    mmsi,
    lat,
    lon,
    sog,
    cog,
    heading,
    name: meta.name || null,
    timestamp: new Date().toISOString(),
    source: 'norway',
  });
  norwayUpsertCount++;
  norwayLastAt = Date.now();
  activeSource = 'norway';
}

function scheduleNorwayReconnect(ms) {
  if (norwayReconnectTimer) clearTimeout(norwayReconnectTimer);
  norwayReconnectTimer = setTimeout(connectNorwayAis, ms);
}

function connectNorwayAis() {
  if (norwaySocket) {
    try { norwaySocket.destroy(); } catch (_) {}
    norwaySocket = null;
  }
  norwayBuf = '';
  console.log('[ais] connecting Kystverket Norway AIS', NORWAY_AIS_HOST + ':' + NORWAY_AIS_PORT);
  const sock = net.connect({ host: NORWAY_AIS_HOST, port: NORWAY_AIS_PORT });
  norwaySocket = sock;

  sock.setKeepAlive(true, 30000);
  sock.setEncoding('utf8');

  sock.on('connect', () => {
    console.log('[ais] Norway AIS TCP connected');
    writeStatus({
      ok: true,
      configured: true,
      norwayConnected: true,
      coverage: 'Digitraffic (Finnish/Baltic) + Kystverket Norway open AIS (EEZ/Svalbard) — no transceiver',
    });
  });

  sock.on('data', (chunk) => {
    norwayBuf += chunk;
    let idx;
    while ((idx = norwayBuf.indexOf('\n')) >= 0) {
      const line = norwayBuf.slice(0, idx);
      norwayBuf = norwayBuf.slice(idx + 1);
      handleNorwayNmea(line.replace(/\r/g, ''));
    }
    // Prevent unbounded buffer
    if (norwayBuf.length > 1e6) norwayBuf = norwayBuf.slice(-10000);
  });

  sock.on('error', (err) => {
    console.error('[ais] Norway AIS error', err.message);
    writeStatus({ norwayConnected: false, error: 'Norway AIS: ' + err.message });
  });

  sock.on('close', () => {
    console.error('[ais] Norway AIS socket closed — reconnecting');
    writeStatus({ norwayConnected: false });
    scheduleNorwayReconnect(8000);
  });
}

setInterval(() => {
  const cutoff = Date.now() - 30 * 60 * 1000;
  for (const [mmsi, rec] of positions) {
    const t = Date.parse(rec.timestamp || 0);
    if (Number.isFinite(t) && t < cutoff) positions.delete(mmsi);
  }
  writeLive();
  maybeResubscribe();
  if (norwayLastAt && Date.now() - norwayLastAt < 60000) {
    writeStatus({
      ok: true,
      configured: true,
      primary: 'digitraffic+norway',
      norwayConnected: !!(norwaySocket && !norwaySocket.destroyed),
      norwayMsgCount,
      norwayUpsertCount,
      coverage: 'Digitraffic (Finnish/Baltic) + Kystverket Norway open AIS — no transceiver',
      error: null,
    });
  }
}, 10000);

digitrafficTimer = setInterval(() => { pollDigitraffic().catch(() => {}); }, 30000);
hubTimer = setInterval(() => { pollAisHub().catch(() => {}); }, 60000);

ensureDataDir();
loadSeismicFleet();
writeLive();
writeStatus({
  ok: false,
  configured: true,
  primary: 'digitraffic+norway',
  error: 'Starting Digitraffic + Norway AIS…',
  coverage: 'Digitraffic (Finnish/Baltic) + Kystverket Norway open AIS — no transceiver',
});
refreshDigitrafficMeta()
  .then(() => pollDigitraffic())
  .catch(() => pollDigitraffic());
connectNorwayAis();
connectOptionalStream();
setTimeout(() => { pollAisHub().catch(() => {}); }, 5000);
console.log('[ais] daemon started (Digitraffic + Norway open AIS — no transceiver required)');
