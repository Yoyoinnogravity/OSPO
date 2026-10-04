#!/usr/bin/env node
/**
 * Route computer steps. The passage desk calls this. The browser does not.
 *   node ship-route-cli.mjs prepare <job.json>
 *   node ship-route-cli.mjs advise <job.json>
 */
import fs from 'fs';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const Advisor = require('./ship-route-advisor.js');

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

const mode = process.argv[2];
const jobPath = process.argv[3];
if ((mode !== 'prepare' && mode !== 'advise') || !jobPath) {
  fail('Use: node ship-route-cli.mjs prepare|advise <job.json>');
}

const job = JSON.parse(fs.readFileSync(jobPath, 'utf8'));
const order = job.order;
if (!order || !order.origin || !order.dest) fail('Job has no passage.');

if (mode === 'prepare') {
  const candidates = Advisor.buildCandidates(order.origin, order.dest);
  job.candidates = candidates;
  job.bounds = Advisor.boundsOf(candidates, 0.75);
  fs.writeFileSync(jobPath, JSON.stringify(job));
  process.exit(0);
}

if (!job.field) fail('Job has no NOAA field yet.');
const advice = Advisor.advise({
  origin: order.origin,
  dest: order.dest,
  vessel: order.vessel,
  stwKt: order.stwKt,
  candidates: job.candidates,
  field: job.field
});
job.status = 'ready';
job.finishedAt = new Date().toISOString();
job.result = {
  ok: !!advice.ok,
  advice: advice.advice || '',
  savedHours: advice.savedHours == null ? null : round(advice.savedHours, 2),
  best: slimRoute(advice.best),
  direct: slimRoute(advice.direct),
  routes: (advice.routes || []).map(slimRoute)
};
delete job.field;
delete job.candidates;
delete job.error;
fs.writeFileSync(jobPath, JSON.stringify(job));
