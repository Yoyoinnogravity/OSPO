<?php
header('Content-Type: application/json');
header('Cache-Control: no-store');
header('Access-Control-Allow-Origin: *');

$statusFile = '/var/www/candooka/data/ais-status.json';
$status = is_readable($statusFile) ? (json_decode(@file_get_contents($statusFile), true) ?: []) : [];

$src = $status['activeSource'] ?? null;
$label = 'AISStream primary + AISHub fallback (coastal). Density layers for planning. Offshore needs satellite (e.g. Kpler).';
if ($src === 'aishub') $label = 'AISHub fallback active (coastal). Add AISStream key for live stream.';
if ($src === 'aisstream') $label = 'AISStream live (coastal). AISHub used if stream drops.';

echo json_encode([
    'configured' => !empty($status['configured']),
    'ok' => !empty($status['ok']),
    'error' => $status['error'] ?? (empty($status['configured'])
        ? 'Add free AISSTREAM_API_KEY at /etc/candooka/ais.env (https://aisstream.io); optional AISHUB_USERNAME'
        : null),
    'vesselCount' => $status['vesselCount'] ?? 0,
    'updatedAt' => $status['updatedAt'] ?? null,
    'activeSource' => $src,
    'fallback' => !empty($status['fallback']),
    'source' => $label,
]);
