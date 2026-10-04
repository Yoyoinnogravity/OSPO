#!/usr/bin/env node
/**
 * Route computer steps. The passage desk calls this. The browser does not.
 *   node ship-route-cli.mjs prepare <job.json>
 *   node ship-route-cli.mjs predict <job.json>
 */
import fs from 'fs';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const Advisor = require('./ship-route-advisor.js');
const Predict = require('./ship-route-predict.js');

function fail(msg) {
  console.error(msg);
  process.exit(1);
}

function round(n, d) {
  if (n == null || !isFinite(n)) return null;
  const p = 10 ** d;
  return Math.round(n * p) / p;
}

function slimRoute(route) {
  if (!route) return null;
  return {
    id: route.id,
    label: route.label,
    offsetNm: round(route.offsetNm, 1),
    distanceNm: round(route.distanceNm, 1),
    sailHours: round(route.sailHours, 2),
    meanCurrentKt: round(route.meanCurrentKt, 2),
    maxHsM: round(route.maxHsM, 2),
    withinLimits: !!route.withinLimits,
    valid: !!route.valid,
    points: (route.points || []).map((p) => ({ lat: round(p.lat, 4), lon: round(p.lon, 4) }))
  };
}

function writeProgress(jobPath, progress) {
  const side = jobPath.replace(/\.json$/, '.progress.json');
  fs.writeFileSync(side, JSON.stringify(progress));
}

const mode = process.argv[2];
const jobPath = process.argv[3];
if ((mode !== 'prepare' && mode !== 'predict') || !jobPath) {
  fail('Use: node ship-route-cli.mjs prepare|predict <job.json>');
}

const job = JSON.parse(fs.readFileSync(jobPath, 'utf8'));
const order = job.order;
if (!order || !order.origin || !order.dest) fail('Job has no passage.');

if (mode === 'prepare') {
  const dist = Advisor.havNm(order.origin, order.dest);
  if (Advisor.crossesDateline(order.origin, order.dest) || dist < 8) {
    const advice = Predict.predictPassage({
      origin: order.origin,
      dest: order.dest,
      vessel: order.vessel,
      stwKt: order.stwKt,
      frames: []
    });
    job.status = 'ready';
    job.finishedAt = new Date().toISOString();
    job.result = { ok: false, advice: advice.advice || '' };
    fs.writeFileSync(jobPath, JSON.stringify(job));
    process.exit(0);
  }
  job.bounds = Predict.searchBounds(order.origin, order.dest);
  job.horizonHours = Predict.horizonHours(dist, order.stwKt || 12);
  fs.writeFileSync(jobPath, JSON.stringify(job));
  process.exit(0);
}

const forecast = job.forecast;
if (!forecast || !forecast.frames || !forecast.frames.length) fail('Job has no NOAA forecast yet.');
let lastWrite = 0;
const advice = Predict.predictPassage({
  origin: order.origin,
  dest: order.dest,
  vessel: order.vessel,
  stwKt: order.stwKt,
  frames: forecast.frames,
  onProgress(progress) {
    const now = Date.now();
    if (now - lastWrite < 400) return;
    lastWrite = now;
    writeProgress(jobPath, progress);
  }
});
job.status = 'ready';
job.finishedAt = new Date().toISOString();
job.result = {
  ok: !!advice.ok,
  advice: advice.advice || '',
  savedHours: advice.savedHours == null ? null : round(advice.savedHours, 2),
  best: slimRoute(advice.best),
  direct: slimRoute(advice.direct),
  routes: (advice.routes || []).map(slimRoute),
  stats: advice.stats || null
};
delete job.forecast;
delete job.field;
delete job.candidates;
delete job.error;
fs.writeFileSync(jobPath, JSON.stringify(job));
