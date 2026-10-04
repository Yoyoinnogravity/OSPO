#!/usr/bin/env node
/**
 * Commercial passage desk: the browser posts a job. The route computer times it.
 * This test uses a synthetic NOAA field, so it does not call ERDDAP.
 */
import fs from 'fs';
import os from 'os';
import path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'candooka-route-'));
const checker = path.join(dir, 'check.php');
fs.writeFileSync(checker, `<?php
require ${JSON.stringify(path.join(__dirname, 'api/ship-route-store.php'))};
list($bad, $err) = ship_route_job_create(['vessel' => 'ferry']);
if ($err === null) { fwrite(STDERR, "ferry was accepted\\n"); exit(1); }
list($job, $err2) = ship_route_job_create([
  'vessel' => 'tanker',
  'stwKt' => 12,
  'reference' => 'Desk test',
  'origin' => ['lat' => 0, 'lon' => 100],
  'dest' => ['lat' => 0, 'lon' => 102],
]);
if ($err2) { fwrite(STDERR, $err2); exit(1); }
if (($job['status'] ?? '') !== 'queued') exit(2);
echo $job['id'];
`);

const id = execFileSync('php', [checker], {
  env: { ...process.env, CANDOOKA_ROUTE_JOBS: dir },
  encoding: 'utf8'
}).trim();
assert(/^[a-f0-9]{32}$/.test(id), 'job id missing: ' + id);

const jobPath = path.join(dir, id + '.json');
execFileSync('node', [path.join(__dirname, 'ship-route-cli.mjs'), 'prepare', jobPath], { encoding: 'utf8' });
const prepared = JSON.parse(fs.readFileSync(jobPath, 'utf8'));
assert(prepared.bounds && prepared.bounds.east > prepared.bounds.west, 'prepare must write a search box');
assert(prepared.candidates.some((r) => r.id === 'direct'), 'prepare must include the straight line');

prepared.field = {
  time: '2026-10-04T00:00:00Z',
  currents: { lats: [-2, 2], lons: [99, 103], u: [[0, 0], [0, 0]], v: [[0, 0], [0, 0]] },
  wind: { lats: [-2, 2], lons: [99, 103], u: [[0, 0], [0, 0]], v: [[0, 0], [0, 0]] },
  waves: { lats: [-2, 2], lons: [99, 103], hs: [[1, 1], [1, 1]], dir: [[90, 90], [90, 90]] }
};
fs.writeFileSync(jobPath, JSON.stringify(prepared));
execFileSync('node', [path.join(__dirname, 'ship-route-cli.mjs'), 'advise', jobPath], { encoding: 'utf8' });
const done = JSON.parse(fs.readFileSync(jobPath, 'utf8'));
assert(done.status === 'ready', 'advise must mark the job ready');
assert(!done.field, 'the stored ticket must not keep the NOAA grid');
assert(done.result && done.result.ok && done.result.best.id === 'direct', 'calm field should keep the straight line');
assert(done.result.advice.includes('NOAA'), done.result.advice);

const page = fs.readFileSync(path.join(__dirname, 'route/index.html'), 'utf8');
const desk = fs.readFileSync(path.join(__dirname, 'route/desk.js'), 'utf8');
assert(page.includes('Send to the route computer'), 'passage desk needs a send button');
assert(page.includes('does not run on your machine'), 'the desk must say the search is not on the customer machine');
assert(desk.includes('/api/ship-route-job.php'), 'the desk must post to the job API');
assert(desk.includes('poll'), 'the desk must poll instead of waiting inside the request');

console.log(JSON.stringify({ ok: true, id, best: done.result.best.id, status: done.status }, null, 2));
