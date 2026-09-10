<?php
// Point depth / elevation. Global ETOPO first (GEBCO GetFeatureInfo is no longer queryable).
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$lat = isset($_GET['lat']) ? floatval($_GET['lat']) : null;
$lon = isset($_GET['lon']) ? floatval($_GET['lon']) : null;

if ($lat === null || $lon === null) {
    echo json_encode(['error' => 'Missing lat/lon']);
    exit;
}
$lat = max(-89.99, min(89.99, $lat));
while ($lon < -180) $lon += 360;
while ($lon > 180) $lon -= 360;

$ctx = stream_context_create([
    'http' => [
        'timeout' => 6,
        'header' => "User-Agent: CandookaOSPO/1.0\r\nAccept: application/json\r\n"
    ]
]);

function depth_ok($z) {
    return is_numeric($z) && is_finite(floatval($z));
}

// 1) ETOPO 1′ via ERDDAP — worldwide
$url = sprintf(
    'https://coastwatch.pfeg.noaa.gov/erddap/griddap/etopo180.json?altitude[(%s):1:(%s)][(%s):1:(%s)]',
    number_format($lat, 4, '.', ''),
    number_format($lat, 4, '.', ''),
    number_format($lon, 4, '.', ''),
    number_format($lon, 4, '.', '')
);
$raw = @file_get_contents($url, false, $ctx);
if ($raw) {
    $j = json_decode($raw, true);
    if (isset($j['table']['rows'][0][2]) && depth_ok($j['table']['rows'][0][2])) {
        $z = floatval($j['table']['rows'][0][2]);
        echo json_encode(['elevation' => $z, 'source' => 'ETOPO']);
        exit;
    }
}

// 2) NOAA global DEM mosaic identify
$url2 = 'https://gis.ngdc.noaa.gov/arcgis/rest/services/DEM_mosaics/DEM_global_mosaic/ImageServer/identify'
      . '?geometry=' . rawurlencode($lon . ',' . $lat)
      . '&geometryType=esriGeometryPoint&sr=4326&f=json';
$raw2 = @file_get_contents($url2, false, $ctx);
if ($raw2) {
    $j2 = json_decode($raw2, true);
    if (isset($j2['value']) && $j2['value'] !== 'NoData' && depth_ok($j2['value'])) {
        echo json_encode(['elevation' => floatval($j2['value']), 'source' => 'NOAA DEM']);
        exit;
    }
}

echo json_encode(['error' => 'Depth lookup failed']);
