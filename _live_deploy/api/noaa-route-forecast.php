<?php
// Forecast frames for the passage prediction.
// Wind (GFS) and waves (WAVEWATCH III) at several hours ahead.
// Currents are the latest daily altimetry map, held on every frame.
// CLI: php noaa-route-forecast.php <south> <north> <west> <east> <horizonHours>

if (PHP_SAPI === 'cli' && isset($argv[1])) {
    $_GET['south'] = $argv[1];
    $_GET['north'] = $argv[2] ?? '';
    $_GET['west'] = $argv[3] ?? '';
    $_GET['east'] = $argv[4] ?? '';
    $_GET['hours'] = $argv[5] ?? '72';
}

header('Content-Type: application/json');
header('Cache-Control: no-store');

$south = isset($_GET['south']) ? floatval($_GET['south']) : null;
$north = isset($_GET['north']) ? floatval($_GET['north']) : null;
$west  = isset($_GET['west'])  ? floatval($_GET['west'])  : null;
$east  = isset($_GET['east'])  ? floatval($_GET['east'])  : null;
$horizon = isset($_GET['hours']) ? intval($_GET['hours']) : 72;
if ($horizon < 12) $horizon = 12;
if ($horizon > 120) $horizon = 120;

if ($south === null || $north === null || $west === null || $east === null
    || $south < -80 || $north > 80 || $south >= $north
    || $west < -180 || $east > 180 || $east <= $west
    || ($north - $south) > 40 || ($east - $west) > 80) {
    http_response_code(400);
    echo json_encode(['error' => 'Forecast box is invalid or too large. Keep the passage on one side of the date line.']);
    exit;
}

function lon360($lon) {
    $x = fmod($lon, 360.0);
    if ($x < 0) $x += 360.0;
    return $x;
}

function snapStep($v, $step) {
    return round($v / $step) * $step;
}

function lonRanges360($west, $east) {
    if ($west < 0 && $east > 0) {
        $w = lon360($west);
        if ($w > 359.5) $w = 359.5;
        return [[$w, 359.5], [0.0, $east]];
    }
    $w = lon360($west);
    $e = lon360($east);
    if ($e < $w) return [[$w, 359.5], [0.0, $e]];
    return [[$w, $e]];
}

function axis($a, $b, $step, $maxCells) {
    $a = snapStep($a, $step);
    $b = snapStep($b, $step);
    if ($b < $a) { $t = $a; $a = $b; $b = $t; }
    if ($b <= $a) $b = $a + $step;
    $n = (int)round(($b - $a) / $step) + 1;
    $stride = (int)max(1, (int)ceil($n / $maxCells));
    return [$a, $b, $stride];
}

function erddapBracket($inner) {
    return '%5B' . rawurlencode($inner) . '%5D';
}

function curlHandle($url) {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_MAXREDIRS => 3,
        CURLOPT_TIMEOUT => 28,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_HTTPHEADER => [
            'User-Agent: CandookaOSPO/1.0 (admin@candooka.world)',
            'Accept: application/json',
        ],
    ]);
    return $ch;
}

function multiJson($urls) {
    if (!$urls) return [];
    $mh = curl_multi_init();
    $handles = [];
    foreach ($urls as $key => $url) {
        $ch = curlHandle($url);
        curl_multi_add_handle($mh, $ch);
        $handles[$key] = $ch;
    }
    $active = null;
    do {
        $status = curl_multi_exec($mh, $active);
        if ($active) curl_multi_select($mh, 1.0);
    } while ($active && $status === CURLM_OK);
    $out = [];
    foreach ($handles as $key => $ch) {
        $raw = curl_multi_getcontent($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_multi_remove_handle($mh, $ch);
        curl_close($ch);
        if ($code < 200 || $code >= 300 || !$raw) {
            $out[$key] = null;
            continue;
        }
        $j = json_decode($raw, true);
        $out[$key] = (is_array($j) && !empty($j['table']['rows'])) ? $j : null;
    }
    curl_multi_close($mh);
    return $out;
}

function gridFromRows($json, $vars, $keyDecimals) {
    if (!$json) return null;
    $cols = $json['table']['columnNames'];
    $idx = array_flip($cols);
    foreach ($vars as $name) {
        if (!isset($idx[$name])) return null;
    }
    if (!isset($idx['latitude']) || !isset($idx['longitude'])) return null;
    $fmt = '%.' . (int)$keyDecimals . 'f';
    $latSet = [];
    $lonSet = [];
    $bag = [];
    $time = '';
    foreach ($json['table']['rows'] as $r) {
        if ($time === '' && isset($idx['time'])) $time = (string)$r[$idx['time']];
        $la = floatval($r[$idx['latitude']]);
        $lo = floatval($r[$idx['longitude']]);
        if ($lo > 180) $lo -= 360;
        $vals = [];
        $ok = true;
        foreach ($vars as $name) {
            $raw = $r[$idx[$name]];
            if (!is_numeric($raw) || strcasecmp((string)$raw, 'NaN') === 0) { $ok = false; break; }
            $vals[$name] = round(floatval($raw), 4);
        }
        if (!$ok) continue;
        $lk = sprintf($fmt, $la);
        $okey = sprintf($fmt, $lo);
        $latSet[$lk] = $la;
        $lonSet[$okey] = $lo;
        $bag[$lk . '|' . $okey] = $vals;
    }
    if (!$latSet) return null;
    $lats = array_values($latSet);
    $lons = array_values($lonSet);
    sort($lats, SORT_NUMERIC);
    sort($lons, SORT_NUMERIC);
    $planes = [];
    foreach ($vars as $name) $planes[$name] = [];
    foreach ($lats as $la) {
        $lk = sprintf($fmt, $la);
        foreach ($vars as $name) {
            $row = [];
            foreach ($lons as $lo) {
                $k = $lk . '|' . sprintf($fmt, $lo);
                $row[] = isset($bag[$k]) ? $bag[$k][$name] : null;
            }
            $planes[$name][] = $row;
        }
    }
    return ['lats' => $lats, 'lons' => $lons, 'planes' => $planes, 'time' => $time];
}

function packPlane($grid, $map) {
    if (!$grid) return null;
    $out = ['lats' => $grid['lats'], 'lons' => $grid['lons'], 'time' => $grid['time']];
    foreach ($map as $from => $to) $out[$to] = $grid['planes'][$from];
    return $out;
}

function mergeJson($parts) {
    $rows = [];
    $cols = null;
    foreach ($parts as $j) {
        if (!$j) continue;
        $cols = $j['table']['columnNames'];
        foreach ($j['table']['rows'] as $r) $rows[] = $r;
    }
    if (!$cols || !$rows) return null;
    return ['table' => ['columnNames' => $cols, 'rows' => $rows]];
}

$maxCells = 16;
list($lat0, $lat1, $latStride) = axis($south, $north, 0.5, $maxCells);
$ranges = [];
foreach (lonRanges360($west, $east) as $rng) {
    $lon0 = snapStep($rng[0], 0.5);
    $lon1 = snapStep($rng[1], 0.5);
    if ($lon1 <= $lon0) $lon1 = $lon0 + 0.5;
    $n = (int)round(($lon1 - $lon0) / 0.5) + 1;
    $lonStride = (int)max(1, (int)ceil($n / $maxCells));
    $ranges[] = [$lon0, $lonStride, $lon1];
}

$offsets = array_values(array_filter([0, 6, 12, 18, 24, 36, 48, 72, 96, 120], function ($h) use ($horizon) {
    return $h <= $horizon;
}));
$stamps = [];
foreach ($offsets as $h) {
    $stamps[] = gmdate('Y-m-d\TH:00:00\Z', time() + $h * 3600);
}

$windHosts = [
    'https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ncep_global.json',
    'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NCEP_Global_Best.json',
];
$waveHosts = [
    'https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ww3_global.json',
    'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NWW3_Global_Best.json',
];

function sliceUrls($hosts, $kind, $stamp, $lat0, $latStride, $lat1, $ranges) {
    $urls = [];
    $tb = erddapBracket('(' . $stamp . ')');
    foreach ($ranges as $ri => $rng) {
        list($lon0, $lonStride, $lon1) = $rng;
        if ($kind === 'wind') {
            $q = sprintf(
                '?ugrd10m%s%%5B(%.1f):%d:(%.1f)%%5D%%5B(%.1f):%d:(%.1f)%%5D,vgrd10m%s%%5B(%.1f):%d:(%.1f)%%5D%%5B(%.1f):%d:(%.1f)%%5D',
                $tb, $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1,
                $tb, $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1
            );
        } else {
            $pt = sprintf('%s%%5B(0.0)%%5D%%5B(%.1f):%d:(%.1f)%%5D%%5B(%.1f):%d:(%.1f)%%5D', $tb, $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1);
            $q = '?Thgt' . $pt . ',Tdir' . $pt;
        }
        foreach ($hosts as $hi => $host) {
            $urls[$kind . '|' . $stamp . '|' . $ri . '|' . $hi] = $host . $q;
        }
    }
    return $urls;
}

function hostSlice($hosts, $kind, $stamp, $lat0, $latStride, $lat1, $ranges, $hostIndex) {
    $all = sliceUrls($hosts, $kind, $stamp, $lat0, $latStride, $lat1, $ranges);
    $out = [];
    foreach ($all as $key => $url) {
        if (substr($key, -2) === '|' . $hostIndex) $out[$key] = $url;
    }
    return $out;
}

$urls = [];
foreach ($stamps as $stamp) {
    $urls = array_merge($urls, hostSlice($windHosts, 'wind', $stamp, $lat0, $latStride, $lat1, $ranges, 0));
    $urls = array_merge($urls, hostSlice($waveHosts, 'wave', $stamp, $lat0, $latStride, $lat1, $ranges, 0));
}
$cLat0 = snapStep($south, 0.25);
$cLat1 = snapStep($north, 0.25);
if ($cLat1 <= $cLat0) $cLat1 = $cLat0 + 0.25;
$cN = (int)round(($cLat1 - $cLat0) / 0.25) + 1;
$cLatStride = (int)max(1, (int)ceil($cN / $maxCells));
foreach ($ranges as $ri => $rng) {
    list($lon0, $lonStride, $lon1) = $rng;
    $lon0c = snapStep($lon0, 0.25);
    $lon1c = snapStep($lon1, 0.25);
    if ($lon1c <= $lon0c) $lon1c = $lon0c + 0.25;
    $ln = (int)round(($lon1c - $lon0c) / 0.25) + 1;
    $lonStrideC = (int)max(1, (int)ceil($ln / $maxCells));
    $tb = erddapBracket('(last)');
    $q = sprintf(
        '?ugos%s%%5B(%.2f):%d:(%.2f)%%5D%%5B(%.2f):%d:(%.2f)%%5D,vgos%s%%5B(%.2f):%d:(%.2f)%%5D%%5B(%.2f):%d:(%.2f)%%5D',
        $tb, $cLat0, $cLatStride, $cLat1, $lon0c, $lonStrideC, $lon1c,
        $tb, $cLat0, $cLatStride, $cLat1, $lon0c, $lonStrideC, $lon1c
    );
    $urls['current|' . $ri] = 'https://coastwatch.pfeg.noaa.gov/erddap/griddap/nesdisSSH1day.json' . $q;
}

$got = multiJson($urls);
$fallback = [];
foreach ($stamps as $stamp) {
    $windHit = false;
    $waveHit = false;
    foreach ($ranges as $ri => $unused) {
        if (!empty($got['wind|' . $stamp . '|' . $ri . '|0'])) $windHit = true;
        if (!empty($got['wave|' . $stamp . '|' . $ri . '|0'])) $waveHit = true;
    }
    if (!$windHit) $fallback = array_merge($fallback, hostSlice($windHosts, 'wind', $stamp, $lat0, $latStride, $lat1, $ranges, 1));
    if (!$waveHit) $fallback = array_merge($fallback, hostSlice($waveHosts, 'wave', $stamp, $lat0, $latStride, $lat1, $ranges, 1));
}
if ($fallback) $got = array_merge($got, multiJson($fallback));

function pickGrid($got, $kind, $stamp, $rangeCount, $vars, $decimals) {
    $parts = [];
    for ($ri = 0; $ri < $rangeCount; $ri++) {
        $hit = null;
        for ($hi = 0; $hi < 2; $hi++) {
            $key = $kind . '|' . $stamp . '|' . $ri . '|' . $hi;
            if (!empty($got[$key])) { $hit = $got[$key]; break; }
        }
        if ($hit) $parts[] = $hit;
    }
    $merged = mergeJson($parts);
    return $merged ? gridFromRows($merged, $vars, $decimals) : null;
}

$currentParts = [];
foreach ($ranges as $ri => $unused) {
    if (!empty($got['current|' . $ri])) $currentParts[] = $got['current|' . $ri];
}
$currents = packPlane(gridFromRows(mergeJson($currentParts), ['ugos', 'vgos'], 2), ['ugos' => 'u', 'vgos' => 'v']);

$frames = [];
foreach ($stamps as $stamp) {
    $wind = packPlane(pickGrid($got, 'wind', $stamp, count($ranges), ['ugrd10m', 'vgrd10m'], 1), ['ugrd10m' => 'u', 'vgrd10m' => 'v']);
    $waves = packPlane(pickGrid($got, 'wave', $stamp, count($ranges), ['Thgt', 'Tdir'], 1), ['Thgt' => 'hs', 'Tdir' => 'dir']);
    if (!$wind && !$waves) continue;
    $frames[] = [
        'time' => ($waves['time'] ?? null) ?: (($wind['time'] ?? null) ?: $stamp),
        'wind' => $wind,
        'waves' => $waves,
        'currents' => $currents,
    ];
}

if (!$frames) {
    http_response_code(502);
    echo json_encode(['error' => 'NOAA did not return a wind or wave forecast for this passage.']);
    exit;
}

echo json_encode([
    'ok' => true,
    'frames' => $frames,
    'currentsHeld' => $currents ? true : false,
    'requestedHours' => $horizon,
    'note' => 'GFS wind and WAVEWATCH III waves at several forecast hours. Geostrophic currents are the latest daily map, held on every frame.',
]);
