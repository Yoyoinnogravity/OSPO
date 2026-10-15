<?php
// Single-vessel AIS position (coastal cache: AISStream + optional AISHub)
header('Content-Type: application/json');
header('Cache-Control: no-store');
header('Access-Control-Allow-Origin: *');

$mmsi = preg_replace('/\D/', '', $_GET['mmsi'] ?? '');
if (strlen($mmsi) !== 9) {
    http_response_code(400);
    echo json_encode(['error' => 'MMSI must be 9 digits']);
    exit;
}

$statusFile = '/var/www/candooka/data/ais-status.json';
$cacheFile  = '/var/www/candooka/data/ais-live.json';
$wantedFile = '/var/www/candooka/data/ais-wanted.json';

$status = is_readable($statusFile) ? (json_decode(@file_get_contents($statusFile), true) ?: []) : [];
if (empty($status['configured'])) {
    http_response_code(503);
    echo json_encode([
        'error' => 'Live AIS daemon not ready. Digitraffic is the default free feed (no transceiver).',
        'configured' => false,
    ]);
    exit;
}

// Queue MMSI for the daemon subscription
$list = is_readable($wantedFile) ? (json_decode(@file_get_contents($wantedFile), true) ?: []) : [];
$list[$mmsi] = time();
foreach ($list as $k => $seen) {
    if ($seen < time() - 3600) unset($list[$k]);
}
@file_put_contents($wantedFile, json_encode($list), LOCK_EX);

if (!is_readable($cacheFile)) {
    echo json_encode(['mmsi' => $mmsi, 'lat' => null, 'lon' => null, 'pending' => true]);
    exit;
}

$positions = json_decode(@file_get_contents($cacheFile), true) ?: [];
if (!isset($positions[$mmsi])) {
    echo json_encode([
        'mmsi' => $mmsi,
        'lat' => null,
        'lon' => null,
        'pending' => true,
        'hint' => 'Waiting for a coastal AIS report — vessel may be out of terrestrial range (use Kpler sat offshore)',
        'feed' => $status['activeSource'] ?? null,
    ]);
    exit;
}

$rec = $positions[$mmsi];
$rec['feed'] = $rec['source'] ?? ($status['activeSource'] ?? null);
echo json_encode($rec);
