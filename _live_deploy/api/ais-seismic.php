<?php
// Seismic acquisition fleet on AIS (roster + live positions from daemon cache)
header('Content-Type: application/json');
header('Cache-Control: no-store');
header('Access-Control-Allow-Origin: *');

$statusFile  = '/var/www/candooka/data/ais-status.json';
$cacheFile   = '/var/www/candooka/data/ais-live.json';
$seismicOn   = '/var/www/candooka/data/ais-seismic-on.json';
$fleetFile   = '/var/www/candooka/ais-service/seismic-fleet.json';

$enable = isset($_GET['enable']) ? $_GET['enable'] : null;
if ($enable !== null) {
    $on = ($enable === '1' || strtolower((string)$enable) === 'true' || $enable === 'on');
    @file_put_contents($seismicOn, json_encode([
        'on' => $on,
        'at' => (int) round(microtime(true) * 1000),
    ]), LOCK_EX);
}

// Keep warm while UI is polling
if (isset($_GET['ping'])) {
    $prev = is_readable($seismicOn) ? (json_decode(@file_get_contents($seismicOn), true) ?: []) : [];
    if (!empty($prev['on'])) {
        @file_put_contents($seismicOn, json_encode([
            'on' => true,
            'at' => (int) round(microtime(true) * 1000),
        ]), LOCK_EX);
    }
}

$status = is_readable($statusFile) ? (json_decode(@file_get_contents($statusFile), true) ?: []) : [];
$live = is_readable($cacheFile) ? (json_decode(@file_get_contents($cacheFile), true) ?: []) : [];
$fleetRaw = is_readable($fleetFile) ? (json_decode(@file_get_contents($fleetFile), true) ?: []) : [];
$roster = isset($fleetRaw['vessels']) && is_array($fleetRaw['vessels']) ? $fleetRaw['vessels'] : (is_array($fleetRaw) ? $fleetRaw : []);

$mode = is_readable($seismicOn) ? (json_decode(@file_get_contents($seismicOn), true) ?: []) : [];
$modeAt = isset($mode['at']) ? floatval($mode['at']) : 0;
$modeOn = !empty($mode['on']) && ((microtime(true) * 1000) - $modeAt < 30 * 60 * 1000);

$working = [];
$silent = [];
$cutoff = time() - 6 * 3600; // seen within 6h = working

foreach ($roster as $v) {
    $mmsi = preg_replace('/\D/', '', (string)($v['mmsi'] ?? ''));
    if (strlen($mmsi) !== 9) continue;
    $pos = $live[$mmsi] ?? null;
    $row = [
        'mmsi' => $mmsi,
        'name' => $v['name'] ?? ($pos['name'] ?? null),
        'imo' => $v['imo'] ?? ($pos['imo'] ?? null),
        'operator' => $v['operator'] ?? ($pos['operator'] ?? null),
        'seismic' => true,
    ];
    if ($pos && isset($pos['lat'], $pos['lon'])) {
        $ts = isset($pos['timestamp']) ? strtotime($pos['timestamp']) : 0;
        $row['lat'] = floatval($pos['lat']);
        $row['lon'] = floatval($pos['lon']);
        $row['sog'] = $pos['sog'] ?? null;
        $row['cog'] = $pos['cog'] ?? null;
        $row['heading'] = $pos['heading'] ?? null;
        $row['timestamp'] = $pos['timestamp'] ?? null;
        $row['source'] = $pos['source'] ?? null;
        $row['working'] = ($ts >= $cutoff);
        if ($row['working']) $working[] = $row;
        else $silent[] = $row;
    } else {
        $row['working'] = false;
        $silent[] = $row;
    }
}

// Also include live vessels tagged seismic but not yet on roster (name discovery)
$rosterSet = [];
foreach ($roster as $v) {
    $m = preg_replace('/\D/', '', (string)($v['mmsi'] ?? ''));
    if ($m) $rosterSet[$m] = true;
}
foreach ($live as $mmsi => $pos) {
    if (!empty($rosterSet[$mmsi])) continue;
    if (empty($pos['seismic'])) continue;
    if (!isset($pos['lat'], $pos['lon'])) continue;
    $ts = isset($pos['timestamp']) ? strtotime($pos['timestamp']) : 0;
    if ($ts < $cutoff) continue;
    $working[] = [
        'mmsi' => (string)$mmsi,
        'name' => $pos['name'] ?? null,
        'imo' => $pos['imo'] ?? null,
        'operator' => $pos['operator'] ?? null,
        'lat' => floatval($pos['lat']),
        'lon' => floatval($pos['lon']),
        'sog' => $pos['sog'] ?? null,
        'cog' => $pos['cog'] ?? null,
        'heading' => $pos['heading'] ?? null,
        'timestamp' => $pos['timestamp'] ?? null,
        'source' => $pos['source'] ?? null,
        'working' => true,
        'discovered' => true,
        'seismic' => true,
    ];
}

usort($working, function ($a, $b) {
    return strcmp($a['name'] ?? $a['mmsi'], $b['name'] ?? $b['mmsi']);
});
usort($silent, function ($a, $b) {
    return strcmp($a['name'] ?? $a['mmsi'], $b['name'] ?? $b['mmsi']);
});

echo json_encode([
    'configured' => !empty($status['configured']),
    'ok' => !empty($status['ok']),
    'error' => $status['error'] ?? (empty($status['configured'])
        ? 'AIS daemon not ready'
        : null),
    'modeOn' => $modeOn,
    'rosterCount' => count($roster),
    'workingCount' => count($working),
    'silentCount' => count($silent),
    'working' => $working,
    'silent' => $silent,
    'feed' => $status['activeSource'] ?? null,
    'updatedAt' => $status['updatedAt'] ?? null,
    'note' => 'Working = AIS hit in last 6 hours. Free Digitraffic covers Finnish/Baltic waters only; global offshore seismic ships need satellite AIS (e.g. Kpler).',
]);
