<?php
// NOAA public-domain marine wind / waves proxy (CoastWatch ERDDAP).
// Wind: NCEP GFS 10 m (ugrd10m / vgrd10m) — NCEP_Global_Best
// Waves: WAVEWATCH III significant wave height / period / direction — NWW3_Global_Best
// Data: https://coastwatch.pfeg.noaa.gov/erddap/ (NOAA / PacIOOS public)

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=21600'); // 6 hours

$mode = isset($_GET['mode']) ? strtolower(trim($_GET['mode'])) : 'wind';
if ($mode !== 'wind' && $mode !== 'waves') {
    http_response_code(400);
    echo json_encode(['error' => 'mode must be wind or waves']);
    exit;
}

$lat = isset($_GET['lat']) ? floatval($_GET['lat']) : null;
$lon = isset($_GET['lon']) ? floatval($_GET['lon']) : null;
if ($lat === null || $lon === null || $lat < -90 || $lat > 90 || $lon < -180 || $lon > 180) {
    http_response_code(400);
    echo json_encode(['error' => 'Valid lat and lon are required']);
    exit;
}

/** Snap to ERDDAP 0.5-deg grid. */
function snapHalf($v) {
    return round($v * 2) / 2;
}

/** Convert lon to ERDDAP 0..359.5 range. */
function lon360($lon) {
    $x = fmod($lon, 360.0);
    if ($x < 0) $x += 360.0;
    return snapHalf($x);
}

function fetchErddapCsv($url) {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_MAXREDIRS => 5,
        CURLOPT_TIMEOUT => 28,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_HTTPHEADER => [
            'User-Agent: CandookaOSPO/1.0 (admin@candooka.world)',
            'Accept: text/csv,application/json',
        ],
    ]);
    $raw = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($code < 200 || $code >= 300 || !$raw) return null;
    // Reject HTML error pages mistaken for CSV
    if (stripos(ltrim($raw), '<') === 0) return null;
    return $raw;
}

/** Try PacIOOS mirror first (CoastWatch redirects here), then CoastWatch. */
function fetchMarineCsv($paths) {
    foreach ($paths as $url) {
        $csv = fetchErddapCsv($url);
        if ($csv) return $csv;
    }
    return null;
}

/** Parse ERDDAP CSV (2 header rows + data). */
function parseErddapCsv($csv) {
    $lines = preg_split("/\r\n|\n|\r/", trim($csv));
    if (!$lines || count($lines) < 3) return null;
    $headers = str_getcsv($lines[0]);
    $row = str_getcsv($lines[2]);
    if (count($row) < count($headers)) return null;
    $out = [];
    foreach ($headers as $i => $h) {
        $out[$h] = $row[$i];
    }
    return $out;
}

function windFromUV($u, $v) {
    $speedMs = sqrt($u * $u + $v * $v);
    // Meteorological FROM direction (degrees)
    $dir = fmod((270.0 - (atan2($v, $u) * 180.0 / M_PI)) + 360.0, 360.0);
    return [
        'speedMs' => $speedMs,
        'speedKt' => $speedMs * 1.943844,
        'dirDeg' => $dir,
    ];
}

function cardinal($deg) {
    $dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
    $i = (int)round($deg / 22.5) % 16;
    return $dirs[$i];
}

$qlat = snapHalf($lat);
$qlon = lon360($lon);

if ($mode === 'wind') {
    // NCEP GFS 10 m — NOAA public domain (PacIOOS / CoastWatch ERDDAP)
    $q = sprintf(
        '?ugrd10m%%5B(last)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D,vgrd10m%%5B(last)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D',
        $qlat, $qlon, $qlat, $qlon
    );
    $csv = fetchMarineCsv([
        'https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ncep_global.csv' . $q,
        'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NCEP_Global_Best.csv' . $q,
    ]);
    $row = $csv ? parseErddapCsv($csv) : null;
    if (!$row || !isset($row['ugrd10m']) || !isset($row['vgrd10m'])
        || !is_numeric($row['ugrd10m']) || !is_numeric($row['vgrd10m'])) {
        http_response_code(502);
        echo json_encode([
            'error' => 'NOAA GFS wind unavailable at this location',
            'lat' => $qlat,
            'lon' => $lon,
            'source' => 'NOAA/NCEP GFS (CoastWatch ERDDAP)',
        ]);
        exit;
    }
    $u = floatval($row['ugrd10m']);
    $v = floatval($row['vgrd10m']);
    $w = windFromUV($u, $v);
    echo json_encode([
        'ok' => true,
        'mode' => 'wind',
        'lat' => $qlat,
        'lon' => $lon,
        'time' => $row['time'] ?? '',
        'uMs' => $u,
        'vMs' => $v,
        'speedMs' => round($w['speedMs'], 2),
        'speedKt' => round($w['speedKt'], 1),
        'dirDeg' => round($w['dirDeg'], 0),
        'dirCardinal' => cardinal($w['dirDeg']),
        'source' => 'NOAA/NCEP GFS 10 m wind (CoastWatch ERDDAP NCEP_Global_Best)',
        'attribution' => 'NOAA NCEP GFS — public domain U.S. Government work',
        'datasetUrl' => 'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NCEP_Global_Best.html',
    ]);
    exit;
}

// Waves — WAVEWATCH III global (NOAA public domain)
$q = sprintf(
    '?Thgt%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D,Tdir%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D,Tper%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D',
    $qlat, $qlon, $qlat, $qlon, $qlat, $qlon
);
$csv = fetchMarineCsv([
    'https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ww3_global.csv' . $q,
    'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NWW3_Global_Best.csv' . $q,
]);
$row = $csv ? parseErddapCsv($csv) : null;
if (!$row || !isset($row['Thgt']) || !is_numeric($row['Thgt'])) {
    http_response_code(502);
    echo json_encode([
        'error' => 'NOAA WAVEWATCH III waves unavailable at this location',
        'lat' => $qlat,
        'lon' => $lon,
        'source' => 'NOAA WAVEWATCH III (CoastWatch ERDDAP)',
    ]);
    exit;
}

$hs = floatval($row['Thgt']);
$tdir = isset($row['Tdir']) && is_numeric($row['Tdir']) ? floatval($row['Tdir']) : null;
$tper = isset($row['Tper']) && is_numeric($row['Tper']) ? floatval($row['Tper']) : null;

echo json_encode([
    'ok' => true,
    'mode' => 'waves',
    'lat' => $qlat,
    'lon' => $lon,
    'time' => $row['time'] ?? '',
    'hsM' => round($hs, 2),
    'hsFt' => round($hs * 3.28084, 1),
    'peakDirDeg' => $tdir !== null ? round($tdir, 0) : null,
    'peakDirCardinal' => $tdir !== null ? cardinal($tdir) : null,
    'peakPeriodSec' => $tper !== null ? round($tper, 1) : null,
    'source' => 'NOAA WAVEWATCH III (CoastWatch ERDDAP NWW3_Global_Best)',
    'attribution' => 'NOAA / NCEP WAVEWATCH III — public domain U.S. Government work',
    'datasetUrl' => 'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NWW3_Global_Best.html',
]);
