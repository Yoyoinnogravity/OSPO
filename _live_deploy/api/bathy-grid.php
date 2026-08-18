<?php
// Sample a global ETOPO 1-arc-minute elevation grid (NOAA via ERDDAP)
// so the client can generate bathymetry contours for the current map view.
// Negative altitude = depth below sea level. Worldwide, not Europe-only.
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=120');

function bathy_fail($msg, $code = 400) {
    http_response_code($code);
    echo json_encode(['error' => $msg]);
    exit;
}

$south = isset($_GET['south']) ? floatval($_GET['south']) : null;
$north = isset($_GET['north']) ? floatval($_GET['north']) : null;
$west  = isset($_GET['west'])  ? floatval($_GET['west'])  : null;
$east  = isset($_GET['east'])  ? floatval($_GET['east'])  : null;
$nx = isset($_GET['nx']) ? intval($_GET['nx']) : 72;
$ny = isset($_GET['ny']) ? intval($_GET['ny']) : 72;

if ($south === null || $north === null || $west === null || $east === null) {
    bathy_fail('Missing south/west/north/east');
}

$nx = max(16, min(96, $nx));
$ny = max(16, min(96, $ny));
$south = max(-89.98, min(89.98, $south));
$north = max(-89.98, min(89.98, $north));
if ($north < $south) { $t = $south; $south = $north; $north = $t; }

// Leaflet can report longitudes outside ±180 when the world is wrapped.
while ($west < -180) $west += 360;
while ($west > 180) $west -= 360;
while ($east < -180) $east += 360;
while ($east > 180) $east -= 360;

$spanLat = max(0.08, $north - $south);
$crossesDateline = ($west > $east);
$spanLon = $crossesDateline ? (360 - $west + $east) : max(0.08, $east - $west);
if ($spanLon > 359) $spanLon = 359;

$strideLat = max(1, (int)floor(($spanLat * 60) / $ny));
$strideLon = max(1, (int)floor(($spanLon * 60) / $nx));
while (($spanLat * 60) / $strideLat > 100) $strideLat++;
while (($spanLon * 60) / $strideLon > 100) $strideLon++;

function bathy_fetch_erddap($south, $west, $north, $east, $strideLat, $strideLon) {
    $url = sprintf(
        'https://coastwatch.pfeg.noaa.gov/erddap/griddap/etopo180.json?altitude[(%s):%d:(%s)][(%s):%d:(%s)]',
        number_format($south, 4, '.', ''),
        $strideLat,
        number_format($north, 4, '.', ''),
        number_format($west, 4, '.', ''),
        $strideLon,
        number_format($east, 4, '.', '')
    );
    $ctx = stream_context_create([
        'http' => [
            'timeout' => 14,
            'header' => "User-Agent: CandookaOSPO/1.0 (bathymetry contours)\r\nAccept: application/json\r\n"
        ]
    ]);
    $raw = @file_get_contents($url, false, $ctx);
    if ($raw === false) return null;
    $json = json_decode($raw, true);
    if (!$json || empty($json['table']['rows'])) return null;
    return $json['table']['rows'];
}

function bathy_reshape($rows) {
    $latSet = [];
    $lonSet = [];
    $vals = [];
    foreach ($rows as $r) {
        if (!isset($r[0], $r[1], $r[2])) continue;
        $lat = round(floatval($r[0]), 6);
        $lon = round(floatval($r[1]), 6);
        $z = floatval($r[2]);
        $latSet[$lat] = true;
        $lonSet[$lon] = true;
        $vals[$lat . '_' . $lon] = $z;
    }
    $lats = array_map('floatval', array_keys($latSet));
    $lons = array_map('floatval', array_keys($lonSet));
    sort($lats, SORT_NUMERIC);
    sort($lons, SORT_NUMERIC);
    $grid = [];
    foreach ($lats as $lat) {
        $row = [];
        foreach ($lons as $lon) {
            $k = $lat . '_' . $lon;
            $row[] = array_key_exists($k, $vals) ? $vals[$k] : null;
        }
        $grid[] = $row;
    }
    return [$lats, $lons, $grid];
}

$rows = [];
if ($crossesDateline) {
    $left = bathy_fetch_erddap($south, $west, $north, 180, $strideLat, $strideLon);
    $right = bathy_fetch_erddap($south, -180, $north, $east, $strideLat, $strideLon);
    if ($left) $rows = array_merge($rows, $left);
    if ($right) {
        foreach ($right as $r) {
            // Keep east-of-dateline longitudes as 180+ so the grid stays monotonic.
            if (isset($r[1]) && $r[1] < 0) $r[1] += 360;
            $rows[] = $r;
        }
    }
} else {
    $rows = bathy_fetch_erddap($south, $west, $north, $east, $strideLat, $strideLon) ?: [];
}

if (!$rows) {
    bathy_fail('ETOPO grid request failed', 502);
}

list($lats, $lons, $grid) = bathy_reshape($rows);
if (count($lats) < 4 || count($lons) < 4) {
    bathy_fail('Not enough bathymetry samples in this view', 422);
}

echo json_encode([
    'source' => 'ETOPO 1-arc-minute (NOAA NCEI via ERDDAP)',
    'units' => 'm',
    'negativeIsDepth' => true,
    'lats' => $lats,
    'lons' => $lons,
    'z' => $grid
]);
