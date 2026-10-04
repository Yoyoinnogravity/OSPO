<?php
// NOAA vector field for ship-route advice.
// One latest-model grid over the passage box:
//   currents — CoastWatch nesdisSSH1day geostrophic ugos/vgos (m/s towards)
//   wind     — GFS 10 m ugrd10m/vgrd10m (m/s towards)
//   waves    — WAVEWATCH III Thgt (m) and Tdir (degrees, waves travel towards)
// Public-domain U.S. Government work via ERDDAP.
// CLI: php noaa-route-field.php <south> <north> <west> <east>

if (PHP_SAPI === 'cli' && isset($argv[1])) {
    $_GET['south'] = $argv[1];
    $_GET['north'] = $argv[2] ?? '';
    $_GET['west'] = $argv[3] ?? '';
    $_GET['east'] = $argv[4] ?? '';
}

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=900');

$south = isset($_GET['south']) ? floatval($_GET['south']) : null;
$north = isset($_GET['north']) ? floatval($_GET['north']) : null;
$west  = isset($_GET['west'])  ? floatval($_GET['west'])  : null;
$east  = isset($_GET['east'])  ? floatval($_GET['east'])  : null;

if ($south === null || $north === null || $west === null || $east === null
    || $south < -80 || $north > 80 || $south >= $north
    || $west < -180 || $east > 180 || $east <= $west
    || ($north - $south) > 80 || ($east - $west) > 160) {
    http_response_code(400);
    echo json_encode(['error' => 'Passage box is invalid or too large for one NOAA field. Keep the route on one side of the date line and under about 160 degrees wide.']);
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

function curlJson($url) {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_MAXREDIRS => 4,
        CURLOPT_TIMEOUT => 40,
        CURLOPT_CONNECTTIMEOUT => 8,
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
    if (!is_array($j) || empty($j['table']['rows'])) return null;
    return $j;
}

function erddapBracket($inner) {
    return '%5B' . rawurlencode($inner) . '%5D';
}

function fetchFirst($urls) {
    foreach ($urls as $url) {
        $j = curlJson($url);
        if ($j) return [$j, $url];
    }
    return [null, null];
}

/** Build north-ascending rows of named variables. Lons stored as -180..180. */
function gridFromRows($json, $vars, $keyDecimals) {
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
    return [
        'lats' => $lats,
        'lons' => $lons,
        'planes' => $planes,
        'time' => $time,
    ];
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

$times = ['(last)', '(' . gmdate('Y-m-d\TH:00:00\Z') . ')'];
$maxCells = 18;

$currents = null;
$currentUrl = null;
list($cLat0, $cLat1, $cLatStride) = axis($south, $north, 0.25, $maxCells);
list($cLon0, $cLon1, $cLonStride) = axis($west, $east, 0.25, $maxCells);
foreach ($times as $tTok) {
    $tb = erddapBracket($tTok);
    $q = sprintf(
        '?ugos%s%%5B(%.2f):%d:(%.2f)%%5D%%5B(%.2f):%d:(%.2f)%%5D,vgos%s%%5B(%.2f):%d:(%.2f)%%5D%%5B(%.2f):%d:(%.2f)%%5D',
        $tb, $cLat0, $cLatStride, $cLat1, $cLon0, $cLonStride, $cLon1,
        $tb, $cLat0, $cLatStride, $cLat1, $cLon0, $cLonStride, $cLon1
    );
    list($j, $url) = fetchFirst([
        'https://coastwatch.pfeg.noaa.gov/erddap/griddap/nesdisSSH1day.json' . $q,
    ]);
    if ($j) {
        $currents = gridFromRows($j, ['ugos', 'vgos'], 2);
        $currentUrl = $url;
        if ($currents) break;
    }
}

function rangedGrid($west, $east, $lat0, $lat1, $latStride, $buildQuery, $hosts, $vars, $decimals) {
    global $times;
    foreach ($times as $tTok) {
        $parts = [];
        $used = null;
        foreach (lonRanges360($west, $east) as $rng) {
            $lon0 = snapStep($rng[0], 0.5);
            $lon1 = snapStep($rng[1], 0.5);
            if ($lon1 <= $lon0) $lon1 = $lon0 + 0.5;
            $n = (int)round(($lon1 - $lon0) / 0.5) + 1;
            $lonStride = (int)max(1, (int)ceil($n / 18));
            $q = $buildQuery($tTok, $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1);
            $urls = [];
            foreach ($hosts as $host) $urls[] = $host . $q;
            list($j, $url) = fetchFirst($urls);
            if ($j) {
                $parts[] = $j;
                $used = $url;
            }
        }
        $merged = mergeJson($parts);
        if ($merged) {
            $grid = gridFromRows($merged, $vars, $decimals);
            if ($grid) return [$grid, $used];
        }
    }
    return [null, null];
}

list($wLat0, $wLat1, $wLatStride) = axis($south, $north, 0.5, $maxCells);
list($wind, $windUrl) = rangedGrid(
    $west, $east, $wLat0, $wLat1, $wLatStride,
    function ($tTok, $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1) {
        $tb = erddapBracket($tTok);
        return sprintf(
            '?ugrd10m%s%%5B(%.1f):%d:(%.1f)%%5D%%5B(%.1f):%d:(%.1f)%%5D,vgrd10m%s%%5B(%.1f):%d:(%.1f)%%5D%%5B(%.1f):%d:(%.1f)%%5D',
            $tb, $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1,
            $tb, $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1
        );
    },
    [
        'https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ncep_global.json',
        'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NCEP_Global_Best.json',
    ],
    ['ugrd10m', 'vgrd10m'],
    1
);

list($waves, $waveUrl) = rangedGrid(
    $west, $east, $wLat0, $wLat1, $wLatStride,
    function ($tTok, $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1) {
        $tb = erddapBracket($tTok);
        $pt = sprintf('%s%%5B(0.0)%%5D%%5B(%.1f):%d:(%.1f)%%5D%%5B(%.1f):%d:(%.1f)%%5D', $tb, $lat0, $latStride, $lat1, $lon0, $lonStride, $lon1);
        return '?Thgt' . $pt . ',Tdir' . $pt;
    },
    [
        'https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ww3_global.json',
        'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NWW3_Global_Best.json',
    ],
    ['Thgt', 'Tdir'],
    1
);

if (!$currents && !$wind && !$waves) {
    http_response_code(502);
    echo json_encode(['error' => 'NOAA currents, wind, and waves were all unavailable for this box']);
    exit;
}

function packPlane($grid, $map) {
    if (!$grid) return null;
    $out = ['lats' => $grid['lats'], 'lons' => $grid['lons'], 'time' => $grid['time']];
    foreach ($map as $from => $to) $out[$to] = $grid['planes'][$from];
    return $out;
}

function gridTime($grid) {
    return (is_array($grid) && !empty($grid['time'])) ? $grid['time'] : '';
}

echo json_encode([
    'ok' => true,
    'time' => gridTime($waves) ?: (gridTime($wind) ?: gridTime($currents)),
    'currents' => packPlane($currents, ['ugos' => 'u', 'vgos' => 'v']),
    'wind' => packPlane($wind, ['ugrd10m' => 'u', 'vgrd10m' => 'v']),
    'waves' => packPlane($waves, ['Thgt' => 'hs', 'Tdir' => 'dir']),
    'source' => [
        'currents' => 'NOAA CoastWatch altimetry geostrophic currents (nesdisSSH1day)',
        'wind' => 'NOAA/NCEP GFS 10 m wind',
        'waves' => 'NOAA WAVEWATCH III significant wave height and direction',
    ],
    'note' => 'Single latest model time for the whole passage. Vectors point in the direction of flow. Wave direction is the direction waves travel towards.',
    'datasetHint' => [
        'currents' => $currentUrl,
        'wind' => $windUrl,
        'waves' => $waveUrl,
    ],
]);
