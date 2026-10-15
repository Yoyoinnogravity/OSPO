<?php
// NOAA sea-surface temperature proxy.
// Latest: MUR preferred, OISST fallback (parallel).
// History: same calendar day last year + year before (tight +/-3 day window if exact day is missing).
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=21600'); // 6 hours

$lat = isset($_GET['lat']) ? floatval($_GET['lat']) : null;
$lon = isset($_GET['lon']) ? floatval($_GET['lon']) : null;
// history=0 disables prior-year lookbacks (default: on)
$wantHistory = !isset($_GET['history']) || $_GET['history'] === '' || $_GET['history'] === '1' || $_GET['history'] === 'true';

if ($lat === null || $lon === null || $lat < -90 || $lat > 90 || $lon < -180 || $lon > 180) {
    http_response_code(400);
    echo json_encode(['error' => 'Valid lat and lon are required']);
    exit;
}

function snap($v, $step, $origin) {
    return round(($v - $origin) / $step) * $step + $origin;
}

function fetchJsonParallel($urls) {
    $mh = curl_multi_init();
    $handles = [];
    foreach ($urls as $key => $url) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 22,
            CURLOPT_HTTPHEADER => [
                'User-Agent: CandookaOSPO/1.0',
                'Accept: application/json',
            ],
        ]);
        curl_multi_add_handle($mh, $ch);
        $handles[$key] = $ch;
    }
    $running = null;
    do {
        curl_multi_exec($mh, $running);
        curl_multi_select($mh);
    } while ($running > 0);

    $out = [];
    foreach ($handles as $key => $ch) {
        $raw = curl_multi_getcontent($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_multi_remove_handle($mh, $ch);
        curl_close($ch);
        $data = ($code >= 200 && $code < 300 && $raw) ? json_decode($raw, true) : null;
        $out[$key] = is_array($data) ? $data : null;
    }
    curl_multi_close($mh);
    return $out;
}

function parseUtcDate($iso) {
    if (!$iso) return null;
    try {
        return new DateTime(substr($iso, 0, 19) . 'Z', new DateTimeZone('UTC'));
    } catch (Exception $e) {
        return null;
    }
}

// Same calendar date N years earlier; Feb 29 -> Feb 28 if needed.
function anniversaryDate(DateTime $ref, $yearsAgo) {
    $y = (int)$ref->format('Y') - (int)$yearsAgo;
    $m = (int)$ref->format('m');
    $d = (int)$ref->format('d');
    if ($m === 2 && $d === 29 && !checkdate(2, 29, $y)) {
        $d = 28;
    }
    $dt = DateTime::createFromFormat('Y-m-d H:i:s', sprintf('%04d-%02d-%02d 09:00:00', $y, $m, $d), new DateTimeZone('UTC'));
    return $dt ?: null;
}

// Tight window: +/- $windowDays around anniversary; pick nearest good row to target day.
function murRangeUrl($lat, $lon, DateTime $center, $windowDays = 3) {
    $start = clone $center;
    $start->modify('-' . (int)$windowDays . ' days');
    $end = clone $center;
    $end->modify('+' . (int)$windowDays . ' days');
    $t0 = $start->format('Y-m-d') . 'T00:00:00Z';
    $t1 = $end->format('Y-m-d') . 'T23:59:59Z';
    return 'https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.json'
        . '?analysed_sst[(' . $t0 . '):(' . $t1 . ')][(' . number_format($lat, 2, '.', '') . ')][(' . number_format($lon, 2, '.', '') . ')]';
}

function pickNearestRow(array $data, DateTime $target) {
    $rows = isset($data['table']['rows']) && is_array($data['table']['rows']) ? $data['table']['rows'] : [];
    $best = null;
    $bestAbs = null;
    $targetTs = $target->getTimestamp();
    foreach ($rows as $row) {
        if (!isset($row[3]) || !is_numeric($row[3])) continue;
        $dt = parseUtcDate(isset($row[0]) ? $row[0] : null);
        if (!$dt) continue;
        $abs = abs($dt->getTimestamp() - $targetTs);
        if ($bestAbs === null || $abs < $bestAbs) {
            $bestAbs = $abs;
            $best = [
                'sstC' => floatval($row[3]),
                'time' => $row[0],
                'lat' => isset($row[1]) ? floatval($row[1]) : null,
                'lon' => isset($row[2]) ? floatval($row[2]) : null,
                'source' => 'NOAA/JPL MUR SST (ERDDAP)',
                'dataset' => 'jplMURSST41',
            ];
        }
    }
    return $best;
}

$murLat = snap($lat, 0.01, 0.0);
$murLon = snap($lon, 0.01, 0.0);
$oiLat = snap($lat, 0.25, -89.875);
$oiLon = snap($lon, 0.25, -179.875);

$urls = [
    'mur' => 'https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.json'
        . '?analysed_sst[(last)][(' . number_format($murLat, 2, '.', '') . ')][(' . number_format($murLon, 2, '.', '') . ')]',
    'oi' => 'https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg_LonPM180.json'
        . '?sst[(last)][(0.0)][(' . number_format($oiLat, 3, '.', '') . ')][(' . number_format($oiLon, 3, '.', '') . ')]',
];

// History anniversaries relative to "today" first; re-anchor to latest obs day after if needed.
$refNow = new DateTime('now', new DateTimeZone('UTC'));
$anniv1 = anniversaryDate($refNow, 1);
$anniv2 = anniversaryDate($refNow, 2);
if ($wantHistory && $anniv1) {
    $urls['mur_y1'] = murRangeUrl($murLat, $murLon, $anniv1, 3);
}
if ($wantHistory && $anniv2) {
    $urls['mur_y2'] = murRangeUrl($murLat, $murLon, $anniv2, 3);
}

$results = fetchJsonParallel($urls);

$body = null;
$mur = $results['mur'];
$row = isset($mur['table']['rows'][0]) ? $mur['table']['rows'][0] : null;
if ($row && isset($row[3]) && is_numeric($row[3])) {
    $body = [
        'sstC' => floatval($row[3]),
        'time' => $row[0],
        'lat' => $row[1],
        'lon' => $row[2],
        'source' => 'NOAA/JPL MUR SST (ERDDAP)',
        'dataset' => 'jplMURSST41',
        'cached' => false,
    ];
}

if (!$body) {
    $oi = $results['oi'];
    $row = isset($oi['table']['rows'][0]) ? $oi['table']['rows'][0] : null;
    if ($row && isset($row[4]) && is_numeric($row[4])) {
        $body = [
            'sstC' => floatval($row[4]),
            'time' => $row[0],
            'lat' => $row[2],
            'lon' => $row[3],
            'source' => 'NOAA OISST v2.1 (ERDDAP)',
            'dataset' => 'ncdcOisst21Agg_LonPM180',
            'cached' => false,
        ];
    }
}

// Align prior-year targets to the latest observation day when available (else "today" UTC).
$refForHistory = $refNow;
if ($body && !empty($body['time'])) {
    $obs = parseUtcDate($body['time']);
    if ($obs) $refForHistory = $obs;
}

$history = [];
if ($wantHistory) {
    foreach ([1, 2] as $yearsAgo) {
        $target = anniversaryDate($refForHistory, $yearsAgo);
        if (!$target) continue;
        $key = 'mur_y' . $yearsAgo;
        $picked = isset($results[$key]) ? pickNearestRow($results[$key], $target) : null;

        // Re-fetch if first batch used today's anniversaries and the obs day is far off, or miss.
        $todayTarget = anniversaryDate($refNow, $yearsAgo);
        $obsOffsetDays = abs($refForHistory->getTimestamp() - $refNow->getTimestamp()) / 86400;
        if ((!$picked || $obsOffsetDays > 2) && $todayTarget) {
            // Prefer target from observation day when it differs; re-query tight window.
            if (!$picked || abs($target->getTimestamp() - $todayTarget->getTimestamp()) > 1 * 86400) {
                $retry = fetchJsonParallel(['h' => murRangeUrl($murLat, $murLon, $target, 3)]);
                $alt = pickNearestRow(isset($retry['h']) ? $retry['h'] : [], $target);
                if ($alt) $picked = $alt;
            }
        }

        if ($picked) {
            $entry = [
                'yearsAgo' => $yearsAgo,
                'label' => $yearsAgo === 1 ? 'Same day last year' : 'Same day year before last',
                'sstC' => $picked['sstC'],
                'time' => $picked['time'],
                'source' => $picked['source'],
                'dataset' => $picked['dataset'],
                'windowDays' => 3,
            ];
            if ($body && isset($body['sstC'])) {
                $entry['deltaC'] = round($body['sstC'] - $picked['sstC'], 2);
            }
            $history[] = $entry;
        }
    }
}

// Latest missing: fall back to prior-year same window for the primary value.
if (!$body && count($history) > 0) {
    $h0 = $history[0];
    $body = [
        'sstC' => $h0['sstC'],
        'time' => $h0['time'],
        'lat' => $murLat,
        'lon' => $murLon,
        'source' => $h0['source'] . ' (prior-year fallback)',
        'dataset' => $h0['dataset'],
        'cached' => false,
        'fallback' => $h0['yearsAgo'] === 1 ? 'same-day-last-year' : 'same-day-year-before-last',
    ];
    // Recompute deltas relative to this fallback
    $history = array_map(function ($h) use ($body) {
        $h['deltaC'] = round($body['sstC'] - $h['sstC'], 2);
        return $h;
    }, $history);
}

if (!$body) {
    http_response_code(404);
    echo json_encode(['error' => 'No SST value at this location (land or missing)']);
    exit;
}

$body['history'] = $history;
echo json_encode($body);
