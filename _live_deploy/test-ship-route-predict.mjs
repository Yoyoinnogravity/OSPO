#!/usr/bin/env node
/**
 * The prediction has to leave a line that is calm now and stormy later.
 * A single snapshot of the first frame would stay on that line.
 */
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const Advisor = require('./ship-route-advisor.js');
const Predict = require('./ship-route-predict.js');

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function zeros(lats, lons) {
  return lats.map(() => lons.map(() => 0));
}

function field(hsFn, box) {
  const south = box ? box.south : -2;
  const north = box ? box.north : 3;
  const west = box ? box.west : 99;
  const east = box ? box.east : 105;
  const lats = [];
  const lons = [];
  for (let la = south; la <= north + 0.001; la += 0.5) lats.push(Math.round(la * 10) / 10);
  for (let lo = west; lo <= east + 0.001; lo += 0.5) lons.push(Math.round(lo * 10) / 10);
  const z = zeros(lats, lons);
  return {
    currents: { lats, lons, u: zeros(lats, lons), v: zeros(lats, lons) },
    wind: { lats, lons, u: z, v: zeros(lats, lons) },
    waves: {
      lats,
      lons,
      hs: lats.map((la) => lons.map((lo) => hsFn(la, lo))),
      dir: lats.map(() => lons.map(() => 270))
    }
  };
}

const origin = { lat: 0, lon: 100 };
const dest = { lat: 0, lon: 104 };
const calm = field(() => 1);
// The storm sits on the middle of the line and builds after departure.
// Both ends stay calm, so a snapshot of the first frame never sees it.
const storm = field((la, lo) => (lo > 100.7 && lo < 103.3 && Math.abs(la) < 0.55 ? 8 : 1.4));
const frames = [
  Object.assign({ time: '2026-10-04T00:00:00Z' }, calm),
  Object.assign({ time: '2026-10-04T12:00:00Z' }, storm),
  Object.assign({ time: '2026-10-05T00:00:00Z' }, storm)
];

const snapshot = Advisor.advise({ origin, dest, vessel: 'tanker', stwKt: 12, field: calm });
assert(snapshot.ok && snapshot.best.id === 'direct', 'a calm snapshot must keep the straight line');

const predicted = Predict.predictPassage({
  origin, dest, vessel: 'tanker', stwKt: 12, frames
});
assert(predicted.ok, predicted.advice);
assert(predicted.best.id !== 'direct', 'the forecast storm should push the ship off the line');
assert(predicted.best.withinLimits, 'the predicted track should stay inside the tanker limit');
assert(predicted.best.maxHsM < 5.5, 'predicted seas ' + predicted.best.maxHsM);
assert(predicted.direct && predicted.direct.maxHsM > 6, 'the straight line should meet the storm, got ' + (predicted.direct && predicted.direct.maxHsM));
assert(predicted.stats.predictions > 1000, 'prediction count ' + predicted.stats.predictions);
assert(predicted.advice.includes('leave the straight line'), predicted.advice);
const around = predicted.best.points.some((p) => Math.abs(p.lat) > 0.6);
assert(around, 'the track should go around the storm, off the line');

const held = Predict.predictPassage({
  origin, dest, vessel: 'tanker', stwKt: 12,
  frames: [Object.assign({ time: '2026-10-04T00:00:00Z' }, calm)]
});
assert(held.ok && held.best.id === 'direct', 'one calm frame should stay on the line: ' + held.advice);

const longer = Predict.predictPassage({
  origin: { lat: 1, lon: 100 },
  dest: { lat: 1, lon: 112 },
  vessel: 'cargo',
  stwKt: 16,
  frames: [Object.assign({ time: '2026-10-04T00:00:00Z' }, field(() => 1.2, { south: -2, north: 4, west: 99, east: 113 }))]
});
assert(longer.ok, longer.advice);
assert(longer.stats.predictions > 8000, 'a longer passage should be a real search, got ' + longer.stats.predictions);
assert(longer.stats.elapsedMs < 20000, 'prediction took ' + longer.stats.elapsedMs + ' ms');

console.log(JSON.stringify({
  ok: true,
  snapshot: snapshot.best.id,
  predicted: predicted.best.id,
  predictedHs: predicted.best.maxHsM,
  directHs: predicted.direct.maxHsM,
  predictions: predicted.stats.predictions,
  longerPredictions: longer.stats.predictions,
  longerMs: longer.stats.elapsedMs
}, null, 2));
