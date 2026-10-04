#!/usr/bin/env node
/**
 * NOAA ship-route advice: tankers and cargo vessels, A to B.
 * Synthetic fields only. Does not call ERDDAP.
 */
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const A = require('./ship-route-advisor.js');

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const origin = { lat: 0, lon: 100 };
const dest = { lat: 0, lon: 102 };

function uniform(sample) {
  return function () { return sample; };
}

const calm = A.advise({
  origin, dest, vessel: 'tanker', stwKt: 12,
  sampleAt: uniform({ currentU: 0, currentV: 0, windU: 0, windV: 0, hsM: 1, waveTowardsDeg: 90 })
});
assert(calm.ok, calm.advice);
assert(calm.best.id === 'direct', 'calm sea must keep the straight line, got ' + calm.best.id);
assert(calm.advice.includes('NOAA'), 'advice must name NOAA');
assert(calm.advice.includes('tanker'), 'advice must name the tanker');
assert(calm.best.withinLimits, '1 m seas are inside the tanker limit');

// Eastbound. A westward current on the equator, still water to the north.
const adverse = A.advise({
  origin, dest, vessel: 'tanker', stwKt: 12,
  sampleAt: function (lat) {
    const bad = lat < 0.15;
    return {
      currentU: bad ? -1.6 : 0,
      currentV: 0,
      windU: 0,
      windV: 0,
      hsM: 1.2,
      waveTowardsDeg: 270
    };
  }
});
assert(adverse.ok, adverse.advice);
assert(adverse.best.offsetNm < 0, 'port (north) track should escape the adverse current, got ' + adverse.best.id);
assert(adverse.savedHours > 0.3, 'offset should save time, saved ' + adverse.savedHours);
assert(adverse.advice.includes('port'), adverse.advice);

// Head seas on the straight line, calm water to the north. Tanker should leave the rough line.
const rough = A.advise({
  origin, dest, vessel: 'tanker', stwKt: 12,
  sampleAt: function (lat, lon) {
    const midRough = Math.abs(lat) < 0.08 && lon > 100.3 && lon < 101.7;
    return {
      currentU: 0, currentV: 0, windU: 0, windV: 0,
      hsM: midRough ? 8 : 1.5,
      waveTowardsDeg: 270
    };
  }
});
assert(rough.ok, rough.advice);
assert(rough.best.id !== 'direct', 'tanker should leave the rough straight line, got ' + rough.best.id);
assert(rough.best.withinLimits, 'calmer track must sit inside the tanker limit');
assert(rough.direct.withinLimits === false, 'straight line at 8 m is outside the tanker limit');

// 6 m everywhere: over the tanker limit (5.5), inside the cargo limit (7).
const six = { currentU: 0, currentV: 0, windU: 0, windV: 0, hsM: 6, waveTowardsDeg: 0 };
const tankerHeavy = A.advise({ origin, dest, vessel: 'tanker', sampleAt: uniform(six) });
const cargoHeavy = A.advise({ origin, dest, vessel: 'cargo', sampleAt: uniform(six) });
assert(tankerHeavy.ok && tankerHeavy.best.withinLimits === false, '6 m must exceed the tanker planning limit');
assert(tankerHeavy.advice.includes('5.5'), tankerHeavy.advice);
assert(cargoHeavy.ok && cargoHeavy.best.withinLimits, '6 m must stay inside the cargo planning limit');
assert(cargoHeavy.advice.includes('cargo'), cargoHeavy.advice);

// Equator samples missing (land or empty NOAA). North offset still has ocean.
const land = A.advise({
  origin, dest, vessel: 'cargo', stwKt: 16,
  sampleAt: function (lat) {
    if (Math.abs(lat) < 0.05) return null;
    return { currentU: 0.2, currentV: 0, windU: 0, windV: 0, hsM: 1, waveTowardsDeg: 90 };
  }
});
assert(land.ok, land.advice);
assert(land.best.id !== 'direct', 'direct track over missing NOAA cells must not win');
assert(land.direct.valid === false, 'direct track should be marked invalid');
assert(!/straight line is the best/.test(land.advice), land.advice);
assert(rough.advice.includes('leave the straight line'), rough.advice);

const dateLine = A.advise({
  origin: { lat: 10, lon: 170 },
  dest: { lat: 12, lon: -170 },
  vessel: 'cargo',
  sampleAt: uniform({ currentU: 0, currentV: 0, windU: 0, windV: 0, hsM: 1, waveTowardsDeg: 0 })
});
assert(dateLine.ok === false, 'date-line passage must be refused');
assert(/date line/i.test(dateLine.advice), dateLine.advice);

const field = {
  time: '2026-10-04T00:00:00Z',
  currents: {
    lats: [-1, 1],
    lons: [99, 103],
    u: [[0, 0], [0, 0]],
    v: [[0, 0], [0, 0]]
  },
  wind: {
    lats: [-1, 1],
    lons: [99, 103],
    u: [[0, 0], [0, 0]],
    v: [[0, 0], [0, 0]]
  },
  waves: {
    lats: [-1, 1],
    lons: [99, 103],
    hs: [[1, 1], [3, 3]],
    dir: [[90, 90], [90, 90]]
  }
};
const mid = A.sampleField(field, 0, 101);
assert(mid && Math.abs(mid.hsM - 2) < 0.05, 'bilinear wave height at the middle should be ~2 m, got ' + (mid && mid.hsM));
const fromField = A.advise({ origin, dest, vessel: 'cargo', stwKt: 16, field });
assert(fromField.ok && fromField.best.id === 'direct', 'uniform-along-track field should keep the straight line');
assert(fromField.advice.includes('2026-10-04'), fromField.advice);

const html = fs.readFileSync(path.resolve(__dirname, 'index.html'), 'utf8');
const app = fs.readFileSync(path.resolve(__dirname, 'app.js'), 'utf8');
assert(html.includes('id="ship-route-vessel"'), 'NOAA panel needs the vessel picker');
assert(html.includes('Advise best route'), 'NOAA panel needs the advise button');
assert(html.includes('ship-route-advisor.js?v=17.42'), 'advisor script cache bump missing');
assert(/app\.js\?v=17\.42/.test(html), 'app.js cache bump 17.42 missing');
assert(app.includes('function adviseShipRoute'), 'app.js must request the NOAA field and draw the advice');
assert(app.includes('api/noaa-route-field.php'), 'advice must load the NOAA route field');
assert(fs.existsSync(path.resolve(__dirname, 'api/noaa-route-field.php')), 'NOAA route field proxy missing');

const candidates = A.buildCandidates(origin, dest);
assert(candidates.some((r) => r.id === 'direct'), 'candidates include the straight line');
assert(candidates.some((r) => r.offsetNm > 0) && candidates.some((r) => r.offsetNm < 0), 'candidates include both sides');

console.log(JSON.stringify({
  ok: true,
  calm: calm.best.id,
  adverse: { id: adverse.best.id, savedHours: +adverse.savedHours.toFixed(2) },
  rough: rough.best.id,
  tankerHeavy: tankerHeavy.best.withinLimits,
  cargoHeavy: cargoHeavy.best.withinLimits,
  land: land.best.id
}, null, 2));
