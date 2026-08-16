<?php
// NOAA real-time map grid proxy for Leaflet image overlays.
// Waves/swell: PacIOOS ww3_global (WAVEWATCH III)
// Wind: PacIOOS ncep_global / CoastWatch NCEP_Global_Best (GFS 10 m)
// Returns a compact lat/lon value grid (JSON) so the client can paint a canvas overlay.
// Public-domain U.S. Government model fields via ERDDAP.

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=900'); // 15 min — model fields update ~hourly

$mode = isset($_GET['mode']) ? strtolower(trim($_GET['mode'])) : 'waves';
$allowed = ['waves', 'swell', 'swell_period', 'wind'];
if (!in_array($mode, $allowed, true)) {
    http_response_code(400);
    echo json_encode(['error' => 'mode must be waves, swell, swell_period, or wind']);
    exit;
}

$south = isset($_GET['south']) ? floatval($_GET['south']) : null;
$north = isset($_GET['north']) ? floatval($_GET['north']) : null;
$west  = isset($_GET['west'])  ? floatval($_GET['west'])  : null;
$east  = isset($_GET['east'])  ? floatval($_GET['east'])  : null;
$maxCells = isset($_GET['maxCells']) ? intval($_GET['maxCells']) : 64;
if ($maxCells < 16) $maxCells = 16;
if ($maxCells > 96) $maxCells = 96;

if ($south === null || $north === null || $west === null || $east === null
    || $south < -90 || $north > 90 || $south >= $north
    || $west < -180 || $east > 180) {
    http_response_code(400);
    echo json_encode(['error' => 'Valid south, west, north, east required (WGS84, west<=east, no antimeridian wrap)']);
    exit;
}

// Limit span so ERDDAP stays responsive
if (($north - $south) > 80 || ($east - $west) > 120) {
    http_response_code(400);
    echo json_encode(['error' => 'Map span too large — zoom in (max ~80° lat × 120° lon)']);
    exit;
}

function lon360($lon) {
    $x = fmod($lon, 360.0);
    if ($x < 0) $x += 360.0;
    return $x;
}

function snapHalf($v) {
    return round($v * 2) / 2;
}

function fetchErddapJson($url) {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_MAXREDIRS => 5,
        CURLOPT_TIMEOUT => 45,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_HTTPHEADER => [
            'User-Agent: CandookaOSPO/1.0 (admin@candooka.world)',
            'Accept: application/json',
        ],
    ]);
    $raw = curl_exec($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($code < 200 || $code >= 300 || !$raw) return null;
    $j = json_decode($raw, true);
    return is_array($j) ? $j : null;
}

/** Snap and stride a 0.5° axis so we stay near maxCells. */
function axisSpec($a, $b, $maxCells) {
    $a = snapHalf($a);
    $b = snapHalf($b);
    if ($b < $a) { $t = $a; $a = $b; $b = $t; }
    $n = (int)round(($b - $a) / 0.5) + 1;
    if ($n < 2) { $b = $a + 0.5; $n = 2; }
    $stride = (int)max(1, (int)ceil($n / $maxCells));
    // ERDDAP stride syntax: (start):stride:(stop) — stride is index step
    return [$a, $b, $stride];
}

$w360 = lon360($west);
$e360 = lon360($east);
// Refuse antimeridian for this endpoint (client should split or zoom)
if ($e360 < $w360) {
    http_response_code(400);
    echo json_encode(['error' => 'Antimeridian spans are not supported — pan so the view does not cross 180°']);
    exit;
}

list($lat0, $lat1, $latStride) = axisSpec($south, $north, $maxCells);
list($lon0, $lon1, $lonStride) = axisSpec($w360, $e360, $maxCells);

$meta = [
    'waves' => [
        'var' => 'Thgt', 'unit' => 'm', 'label' => 'Significant wave height',
        'depth' => true, 'paletteMax' => 8.0,
    ],
    'swell' => [
        'var' => 'shgt', 'unit' => 'm', 'label' => 'Swell height',
        'depth' => true, 'paletteMax' => 5.0,
    ],
    'swell_period' => [
        'var' => 'sper', 'unit' => 's', 'label' => 'Swell period',
        'depth' => true, 'paletteMax' => 20.0,
    ],
    'wind' => [
        'var' => 'speed', 'unit' => 'kt', 'label' => '10 m wind speed',
        'depth' => false, 'paletteMax' => 40.0,
    ],
];
$m = $meta[$mode];

if ($mode === 'wind') {
    $q = sprintf(
        '?ugrd10m%%5B(last)%%5D%%5B(%.1f):%d:(%.1f)%%5D%%5B(%.1f):%d:(%.1f)%%5D'
        . ',vgrd10m%%5B(last)%%5D%%5B(%.1f):%d:(%.1f)%%5D%%5B(%.1f):%d:(%.1f)%%5D',
        $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1,
        $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1
    );
    $urls = [
        'https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ncep_global.json' . $q,
        'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NCEP_Global_Best.json' . $q,
    ];
} else {
    $q = sprintf(
        '?%s%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f):%d:(%.1f)%%5D%%5B(%.1f):%d:(%.1f)%%5D',
        $m['var'], $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1
    );
    $urls = [
        'https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ww3_global.json' . $q,
        'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NWW3_Global_Best.json' . $q,
    ];
}

$json = null;
$used = null;
foreach ($urls as $url) {
    $json = fetchErddapJson($url);
    if ($json && isset($json['table']['rows']) && count($json['table']['rows']) > 0) {
        $used = $url;
        break;
    }
}

if (!$json) {
    http_response_code(502);
    echo json_encode(['error' => 'NOAA ERDDAP grid unavailable', 'mode' => $mode]);
    exit;
}

$table = $json['table'];
$cols = $table['columnNames'];
$rows = $table['rows'];
$idx = array_flip($cols);

$latSet = [];
$lonSet = [];
$byKey = [];
$time = '';

foreach ($rows as $r) {
    if ($time === '' && isset($idx['time'])) $time = (string)$r[$idx['time']];
    $la = floatval($r[$idx['latitude']]);
    $lo = floatval($r[$idx['longitude']]);
    // Present lons in -180..180 for Leaflet
    $loSigned = $lo > 180 ? $lo - 360 : $lo;
    $latSet[sprintf('%.1f', $la)] = $la;
    $lonSet[sprintf('%.1f', $loSigned)] = $loSigned;

    if ($mode === 'wind') {
        $u = $r[$idx['ugrd10m']] ?? null;
        $v = $r[$idx['vgrd10m']] ?? null;
        if (!is_numeric($u) || !is_numeric($v)) continue;
        $val = sqrt(floatval($u) * floatval($u) + floatval($v) * floatval($v)) * 1.943844; // kt
    } else {
        $raw = $r[$idx[$m['var']]] ?? null;
        if (!is_numeric($raw) || strcasecmp((string)$raw, 'NaN') === 0) continue;
        $val = floatval($raw);
    }
    $byKey[sprintf('%.1f|%.1f', $la, $loSigned)] = $val;
}

$lats = array_values($latSet);
$lons = array_values($lonSet);
sort($lats, SORT_NUMERIC);
sort($lons, SORT_NUMERIC);
// Paint north→south so image matches geographic orientation when drawn top-down
$lats = array_reverse($lats);

$values = [];
$min = null;
$max = null;
foreach ($lats as $la) {
    $rowOut = [];
    foreach ($lons as $lo) {
        $k = sprintf('%.1f|%.1f', $la, $lo);
        if (!array_key_exists($k, $byKey)) {
            $rowOut[] = null;
            continue;
        }
        $v = $byKey[$k];
        $rowOut[] = round($v, 2);
        if ($min === null || $v < $min) $min = $v;
        if ($max === null || $v > $max) $max = $v;
    }
    $values[] = $rowOut;
}

if ($min === null) {
    http_response_code(502);
    echo json_encode(['error' => 'No valid NOAA values in this view (land or missing)', 'mode' => $mode]);
    exit;
}

echo json_encode([
    'ok' => true,
    'mode' => $mode,
    'var' => $m['var'],
    'label' => $m['label'],
    'unit' => $m['unit'],
    'time' => $time,
    'paletteMax' => $m['paletteMax'],
    'bounds' => [
        'south' => min($lats),
        'north' => max($lats),
        'west' => min($lons),
        'east' => max($lons),
    ],
    'lats' => $lats,
    'lons' => $lons,
    'values' => $values,
    'min' => round($min, 2),
    'max' => round($max, 2),
    'source' => $mode === 'wind'
        ? 'NOAA/NCEP GFS 10 m (PacIOOS / CoastWatch ERDDAP)'
        : 'NOAA WAVEWATCH III (PacIOOS / CoastWatch ERDDAP)',
    'attribution' => 'NOAA public-domain model field',
    'datasetHint' => $used,
]);
