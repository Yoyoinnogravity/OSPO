<?php
// AIS vessels in a map bounding box (coastal cache: AISStream + optional AISHub)
header('Content-Type: application/json');
header('Cache-Control: no-store');
header('Access-Control-Allow-Origin: *');

$minlat = isset($_GET['minlat']) ? floatval($_GET['minlat']) : null;
$maxlat = isset($_GET['maxlat']) ? floatval($_GET['maxlat']) : null;
$minlon = isset($_GET['minlon']) ? floatval($_GET['minlon']) : null;
$maxlon = isset($_GET['maxlon']) ? floatval($_GET['maxlon']) : null;

if ($minlat === null || $maxlat === null || $minlon === null || $maxlon === null) {
    http_response_code(400);
    echo json_encode(['error' => 'minlat, maxlat, minlon, maxlon required']);
    exit;
}

if ($maxlat < $minlat) { $t = $minlat; $minlat = $maxlat; $maxlat = $t; }
if ($maxlon < $minlon) { $t = $minlon; $minlon = $maxlon; $maxlon = $t; }

// Cap bbox size to keep feed manageable
if (($maxlat - $minlat) > 15) {
    $mid = ($minlat + $maxlat) / 2;
    $minlat = $mid - 7.5; $maxlat = $mid + 7.5;
}
if (($maxlon - $minlon) > 15) {
    $mid = ($minlon + $maxlon) / 2;
    $minlon = $mid - 7.5; $maxlon = $mid + 7.5;
}

$statusFile = '/var/www/candooka/data/ais-status.json';
$cacheFile  = '/var/www/candooka/data/ais-live.json';
$bboxFile   = '/var/www/candooka/data/ais-bbox.json';

$status = is_readable($statusFile) ? (json_decode(@file_get_contents($statusFile), true) ?: []) : [];
if (empty($status['configured'])) {
    http_response_code(503);
    echo json_encode([
        'error' => 'Live AIS not configured. Add free AISSTREAM_API_KEY to /etc/candooka/ais.env (https://aisstream.io). Optional AISHUB_USERNAME for fallback.',
        'configured' => false,
        'vessels' => [],
    ]);
    exit;
}

// Tell daemon which area to listen to
@file_put_contents($bboxFile, json_encode([
    'minlat' => $minlat,
    'maxlat' => $maxlat,
    'minlon' => $minlon,
    'maxlon' => $maxlon,
    'at' => round(microtime(true) * 1000),
]), LOCK_EX);

$positions = is_readable($cacheFile) ? (json_decode(@file_get_contents($cacheFile), true) ?: []) : [];
$out = [];
foreach ($positions as $v) {
    if (!isset($v['lat'], $v['lon'])) continue;
    $lat = floatval($v['lat']); $lon = floatval($v['lon']);
    if ($lat < $minlat || $lat > $maxlat || $lon < $minlon || $lon > $maxlon) continue;
    $out[] = $v;
}

usort($out, function ($a, $b) {
    return strcmp($a['name'] ?? $a['mmsi'] ?? '', $b['name'] ?? $b['mmsi'] ?? '');
});

$src = $status['activeSource'] ?? $status['source'] ?? 'aisstream';
echo json_encode([
    'configured' => true,
    'ok' => !empty($status['ok']),
    'count' => count($out),
    'vessels' => array_slice($out, 0, 500),
    'feed' => $src,
    'status' => [
        'error' => $status['error'] ?? null,
        'vesselCount' => $status['vesselCount'] ?? 0,
        'updatedAt' => $status['updatedAt'] ?? null,
        'activeSource' => $src,
        'fallback' => !empty($status['fallback']),
    ],
]);
