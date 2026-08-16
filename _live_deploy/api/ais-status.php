<?php
header('Content-Type: application/json');
header('Cache-Control: no-store');
header('Access-Control-Allow-Origin: *');

$statusFile = '/var/www/candooka/data/ais-status.json';
$status = is_readable($statusFile) ? (json_decode(@file_get_contents($statusFile), true) ?: []) : [];

$src = $status['activeSource'] ?? null;
$label = 'AISHub primary (coastal). Optional AISStream secondary. Density layers for planning. Offshore needs satellite (e.g. Kpler).';
if ($src === 'aishub') $label = 'AISHub live (coastal).';
if ($src === 'aisstream') $label = 'AISStream secondary active; AISHub remains primary poll.';

echo json_encode([
    'configured' => !empty($status['configured']),
    'ok' => !empty($status['ok']),
    'error' => $status['error'] ?? (empty($status['configured'])
        ? 'Add AISHUB_USERNAME at /etc/candooka/ais.env — join https://www.aishub.net and share a terrestrial AIS feed'
        : null),
    'vesselCount' => $status['vesselCount'] ?? 0,
    'updatedAt' => $status['updatedAt'] ?? null,
    'activeSource' => $src,
    'primary' => $status['primary'] ?? 'aishub',
    'source' => $label,
]);
