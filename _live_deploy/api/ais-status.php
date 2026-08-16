<?php
header('Content-Type: application/json');
header('Cache-Control: no-store');
header('Access-Control-Allow-Origin: *');

$statusFile = '/var/www/candooka/data/ais-status.json';
$status = is_readable($statusFile) ? (json_decode(@file_get_contents($statusFile), true) ?: []) : [];

$src = $status['activeSource'] ?? null;
$label = 'Digitraffic open AIS (Finnish/Baltic coastal — no transceiver). Optional AISHub/AISStream if configured. Offshore sat AIS needs Kpler.';
if ($src === 'digitraffic') $label = 'Digitraffic live (Finnish / Baltic coastal).';
if ($src === 'aishub') $label = 'AISHub optional feed active.';
if ($src === 'aisstream') $label = 'AISStream optional feed active.';

echo json_encode([
    'configured' => !empty($status['configured']),
    'ok' => !empty($status['ok']),
    'error' => $status['error'] ?? null,
    'vesselCount' => $status['vesselCount'] ?? 0,
    'updatedAt' => $status['updatedAt'] ?? null,
    'activeSource' => $src,
    'primary' => $status['primary'] ?? 'digitraffic',
    'coverage' => $status['coverage'] ?? 'Digitraffic open AIS — Finnish / Baltic coastal waters',
    'source' => $label,
]);
