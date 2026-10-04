<?php
// Job files for the commercial passage desk.
// Stored outside the web root so a guessed URL cannot download them.

if (PHP_SAPI !== 'cli' && isset($_SERVER['SCRIPT_FILENAME']) && realpath($_SERVER['SCRIPT_FILENAME']) === realpath(__FILE__)) {
    http_response_code(404);
    exit;
}

function ship_route_job_dir() {
    $dir = getenv('CANDOOKA_ROUTE_JOBS');
    if (!$dir) $dir = sys_get_temp_dir() . '/candooka-route-jobs';
    if (!is_dir($dir)) mkdir($dir, 0700, true);
    return $dir;
}

function ship_route_job_path($id) {
    if (!is_string($id) || !preg_match('/^[a-f0-9]{32}$/', $id)) return null;
    return ship_route_job_dir() . '/' . $id . '.json';
}

function ship_route_job_load($id) {
    $path = ship_route_job_path($id);
    if (!$path || !is_file($path)) return null;
    $job = json_decode((string)file_get_contents($path), true);
    return is_array($job) ? $job : null;
}

function ship_route_job_save($job) {
    $path = ship_route_job_path($job['id'] ?? '');
    if (!$path) return false;
    $tmp = $path . '.tmp';
    file_put_contents($tmp, json_encode($job));
    return rename($tmp, $path);
}

function ship_route_point($p) {
    if (!is_array($p) || !isset($p['lat'], $p['lon']) || !is_numeric($p['lat']) || !is_numeric($p['lon'])) {
        return null;
    }
    $lat = floatval($p['lat']);
    $lon = floatval($p['lon']);
    if ($lat < -80 || $lat > 80 || $lon < -180 || $lon > 180) return null;
    return ['lat' => round($lat, 5), 'lon' => round($lon, 5)];
}

/** @return array{0: ?array, 1: ?string} */
function ship_route_validate_order($in) {
    if (!is_array($in)) return [null, 'Send the passage as JSON.'];
    $vessel = isset($in['vessel']) ? strtolower(trim((string)$in['vessel'])) : 'tanker';
    if ($vessel !== 'tanker' && $vessel !== 'cargo') {
        return [null, 'Vessel must be a tanker or a cargo ship.'];
    }
    $defaultSpeed = $vessel === 'cargo' ? 16 : 12;
    $stw = isset($in['stwKt']) && $in['stwKt'] !== '' ? floatval($in['stwKt']) : $defaultSpeed;
    if ($stw < 4 || $stw > 25) return [null, 'Calm-water speed must be between 4 and 25 kt.'];
    $origin = ship_route_point($in['origin'] ?? null);
    $dest = ship_route_point($in['dest'] ?? null);
    if (!$origin || !$dest) return [null, 'Departure and arrival each need a latitude and a longitude on the water.'];
    $ref = isset($in['reference']) ? trim((string)$in['reference']) : '';
    if (function_exists('mb_substr')) $ref = mb_substr($ref, 0, 80);
    else $ref = substr($ref, 0, 80);
    return [[
        'vessel' => $vessel,
        'stwKt' => $stw,
        'origin' => $origin,
        'dest' => $dest,
        'reference' => $ref,
    ], null];
}

/** @return array{0: ?array, 1: ?string} */
function ship_route_job_create($in) {
    list($order, $err) = ship_route_validate_order($in);
    if ($err) return [null, $err];
    $job = [
        'id' => bin2hex(random_bytes(16)),
        'status' => 'queued',
        'createdAt' => gmdate('c'),
        'order' => $order,
    ];
    if (!ship_route_job_save($job)) return [null, 'The passage desk could not store this order.'];
    return [$job, null];
}

function ship_route_progress_path($id) {
    $path = ship_route_job_path($id);
    if (!$path) return null;
    return substr($path, 0, -5) . '.progress.json';
}

function ship_route_progress_write($id, $progress) {
    $path = ship_route_progress_path($id);
    if (!$path) return false;
    $tmp = $path . '.tmp';
    file_put_contents($tmp, json_encode($progress));
    return rename($tmp, $path);
}

function ship_route_progress_read($id) {
    $path = ship_route_progress_path($id);
    if (!$path || !is_file($path)) return null;
    $progress = json_decode((string)file_get_contents($path), true);
    return is_array($progress) ? $progress : null;
}

function ship_route_job_public($job) {
    return [
        'ok' => true,
        'id' => $job['id'],
        'status' => $job['status'],
        'createdAt' => $job['createdAt'] ?? null,
        'startedAt' => $job['startedAt'] ?? null,
        'finishedAt' => $job['finishedAt'] ?? null,
        'order' => $job['order'] ?? null,
        'error' => $job['error'] ?? null,
        'progress' => ship_route_progress_read($job['id']),
        'result' => $job['result'] ?? null,
        'deskUrl' => '/route/?job=' . $job['id'],
    ];
}
