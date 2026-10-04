<?php
// Route computer. Run from the passage desk, not from the browser.
// php ship-route-run.php <jobId>

if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}

require __DIR__ . '/ship-route-store.php';

$id = $argv[1] ?? '';
$job = ship_route_job_load($id);
if (!$job) exit(1);
if (($job['status'] ?? '') === 'ready') exit(0);

$job['status'] = 'running';
$job['startedAt'] = gmdate('c');
unset($job['error']);
ship_route_job_save($job);

function ship_route_fail($id, $message) {
    $job = ship_route_job_load($id);
    if (!$job) return;
    $job['status'] = 'failed';
    $job['error'] = $message;
    $job['finishedAt'] = gmdate('c');
    unset($job['field'], $job['candidates']);
    ship_route_job_save($job);
}

function ship_route_exec($cmd, &$code) {
    $lines = [];
    exec($cmd . ' 2>&1', $lines, $code);
    return implode("\n", $lines);
}

$node = trim((string)shell_exec('command -v node'));
if ($node === '') {
    ship_route_fail($id, 'The route computer needs Node.js installed beside PHP.');
    exit(1);
}

$cli = dirname(__DIR__) . '/ship-route-cli.mjs';
$jobPath = ship_route_job_path($id);
$prepare = ship_route_exec(
    escapeshellarg($node) . ' ' . escapeshellarg($cli) . ' prepare ' . escapeshellarg($jobPath),
    $code
);
if ($code !== 0) {
    ship_route_fail($id, 'The route computer could not lay out the tracks. ' . trim($prepare));
    exit(1);
}

$job = ship_route_job_load($id);
$bounds = $job['bounds'] ?? null;
if (!is_array($bounds)) {
    ship_route_fail($id, 'The route computer did not return a search box.');
    exit(1);
}

$php = PHP_BINARY ?: 'php';
$fieldCmd = escapeshellarg($php) . ' -d display_errors=0 ' . escapeshellarg(__DIR__ . '/noaa-route-field.php')
    . ' ' . escapeshellarg((string)$bounds['south'])
    . ' ' . escapeshellarg((string)$bounds['north'])
    . ' ' . escapeshellarg((string)$bounds['west'])
    . ' ' . escapeshellarg((string)$bounds['east']);
$field = null;
$fieldCode = 1;
for ($attempt = 0; $attempt < 2; $attempt++) {
    if ($attempt === 1) sleep(3);
    $fieldRaw = ship_route_exec($fieldCmd, $fieldCode);
    $field = json_decode($fieldRaw, true);
    if ($fieldCode === 0 && is_array($field) && !empty($field['ok'])) break;
}
if ($fieldCode !== 0 || !is_array($field) || empty($field['ok'])) {
    $why = is_array($field) && !empty($field['error']) ? $field['error'] : 'NOAA did not return a field for this passage.';
    ship_route_fail($id, $why);
    exit(1);
}

$job = ship_route_job_load($id);
$job['field'] = $field;
ship_route_job_save($job);

$advise = ship_route_exec(
    escapeshellarg($node) . ' ' . escapeshellarg($cli) . ' advise ' . escapeshellarg($jobPath),
    $adviseCode
);
if ($adviseCode !== 0) {
    ship_route_fail($id, 'The route computer stopped while timing the tracks. ' . trim($advise));
    exit(1);
}

exit(0);
