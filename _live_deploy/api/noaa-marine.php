<?php
// NOAA public-domain marine wind / waves proxy (CoastWatch ERDDAP).
// Wind: NCEP GFS 10 m (ugrd10m / vgrd10m) — NCEP_Global_Best
// Waves: WAVEWATCH III significant wave height / period / direction — NWW3_Global_Best
// Data: https://coastwatch.pfeg.noaa.gov/erddap/ (NOAA / PacIOOS public)

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=3600'); // 1 hour — latest WW3 / GFS model fields

$mode = isset($_GET['mode']) ? strtolower(trim($_GET['mode'])) : 'wind';
if ($mode !== 'wind' && $mode !== 'waves' && $mode !== 'swell') {
    http_response_code(400);
    echo json_encode(['error' => 'mode must be wind, waves, or swell']);
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

// Waves / Swell — WAVEWATCH III global (NOAA public domain via PacIOOS)
// Combined sea: Thgt / Tper / Tdir
// Swell (surf): shgt / sper / sdir
// Wind sea: whgt / wper / wdir
$q = sprintf(
    '?Thgt%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D'
    . ',Tdir%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D'
    . ',Tper%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D'
    . ',shgt%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D'
    . ',sper%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D'
    . ',sdir%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D'
    . ',whgt%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D'
    . ',wper%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D'
    . ',wdir%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D',
    $qlat, $qlon, $qlat, $qlon, $qlat, $qlon,
    $qlat, $qlon, $qlat, $qlon, $qlat, $qlon,
    $qlat, $qlon, $qlat, $qlon, $qlat, $qlon
);
$csv = fetchMarineCsv([
    'https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ww3_global.csv' . $q,
    // CoastWatch legacy may lack swell split — fall back to combined only
    'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NWW3_Global_Best.csv' . sprintf(
        '?Thgt%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D,Tdir%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D,Tper%%5B(last)%%5D%%5B(0.0)%%5D%%5B(%.1f)%%5D%%5B(%.1f)%%5D',
        $qlat, $qlon, $qlat, $qlon, $qlat, $qlon
    ),
]);
$row = $csv ? parseErddapCsv($csv) : null;
if (!$row || ((!isset($row['Thgt']) || !is_numeric($row['Thgt']))
    && (!isset($row['shgt']) || !is_numeric($row['shgt'])))) {
    http_response_code(502);
    echo json_encode([
        'error' => 'NOAA WAVEWATCH III swell/waves unavailable at this location',
        'lat' => $qlat,
        'lon' => $lon,
        'source' => 'NOAA WAVEWATCH III (PacIOOS / CoastWatch ERDDAP)',
    ]);
    exit;
}

function numOrNull($row, $key) {
    return (isset($row[$key]) && is_numeric($row[$key]) && strcasecmp((string)$row[$key], 'NaN') !== 0)
        ? floatval($row[$key]) : null;
}

$hs = numOrNull($row, 'Thgt');
$tdir = numOrNull($row, 'Tdir');
$tper = numOrNull($row, 'Tper');
$shgt = numOrNull($row, 'shgt');
$sper = numOrNull($row, 'sper');
$sdir = numOrNull($row, 'sdir');
$whgt = numOrNull($row, 'whgt');
$wper = numOrNull($row, 'wper');
$wdir = numOrNull($row, 'wdir');

// Surf-oriented summary: prefer dedicated swell fields; fall back to combined sea
$surfHs = $shgt !== null ? $shgt : $hs;
$surfPer = $sper !== null ? $sper : $tper;
$surfDir = $sdir !== null ? $sdir : $tdir;

// Rough surfability hint from period (public WW3 model guidance, not a forecast product)
$surfHint = null;
if ($surfPer !== null) {
    if ($surfPer >= 14) $surfHint = 'Long-period swell — typically more organised / powerful for surfing';
    else if ($surfPer >= 10) $surfHint = 'Medium-period swell — often rideable depending on height & local bathymetry';
    else if ($surfPer >= 7) $surfHint = 'Shorter-period energy — can be choppier / windier feel';
    else $surfHint = 'Short period — often wind-sea dominated; less ideal for clean surf';
}

$payload = [
    'ok' => true,
    'mode' => $mode === 'swell' ? 'swell' : 'waves',
    'lat' => $qlat,
    'lon' => $lon,
    'time' => $row['time'] ?? '',
    'hsM' => $hs !== null ? round($hs, 2) : null,
    'hsFt' => $hs !== null ? round($hs * 3.28084, 1) : null,
    'peakDirDeg' => $tdir !== null ? round($tdir, 0) : null,
    'peakDirCardinal' => $tdir !== null ? cardinal($tdir) : null,
    'peakPeriodSec' => $tper !== null ? round($tper, 1) : null,
    'swellHsM' => $shgt !== null ? round($shgt, 2) : null,
    'swellHsFt' => $shgt !== null ? round($shgt * 3.28084, 1) : null,
    'swellPeriodSec' => $sper !== null ? round($sper, 1) : null,
    'swellDirDeg' => $sdir !== null ? round($sdir, 0) : null,
    'swellDirCardinal' => $sdir !== null ? cardinal($sdir) : null,
    'windSeaHsM' => $whgt !== null ? round($whgt, 2) : null,
    'windSeaPeriodSec' => $wper !== null ? round($wper, 1) : null,
    'windSeaDirDeg' => $wdir !== null ? round($wdir, 0) : null,
    'windSeaDirCardinal' => $wdir !== null ? cardinal($wdir) : null,
    // Surfer-facing aliases (latest WW3 model time)
    'surfHsM' => $surfHs !== null ? round($surfHs, 2) : null,
    'surfHsFt' => $surfHs !== null ? round($surfHs * 3.28084, 1) : null,
    'surfPeriodSec' => $surfPer !== null ? round($surfPer, 1) : null,
    'surfDirDeg' => $surfDir !== null ? round($surfDir, 0) : null,
    'surfDirCardinal' => $surfDir !== null ? cardinal($surfDir) : null,
    'surfHint' => $surfHint,
    'source' => 'NOAA WAVEWATCH III via PacIOOS ERDDAP (public domain)',
    'attribution' => 'NOAA / NCEP WAVEWATCH III — public domain U.S. Government work',
    'datasetUrl' => 'https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ww3_global.html',
    'realtimeNote' => 'Latest WW3 model analysis/forecast field (typically hourly). Not a buoy observation.',
];

echo json_encode($payload);