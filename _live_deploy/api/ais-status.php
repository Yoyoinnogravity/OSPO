<?php
header('Content-Type: application/json');
header('Cache-Control: no-store');
header('Access-Control-Allow-Origin: *');

$statusFile = '/var/www/candooka/data/ais-status.json';
$status = is_readable($statusFile) ? (json_decode(@file_get_contents($statusFile), true) ?: []) : [];

$src = $status['activeSource'] ?? null;
$label = 'Free AIS: Digitraffic (Finnish/Baltic) + Kystverket Norway open stream. No transceiver required.';
if ($src === 'digitraffic') $label = 'Digitraffic live (Finnish / Baltic).';
if ($src === 'norway') $label = 'Kystverket Norway open AIS live.';
if ($src === 'aishub') $label = 'AISHub optional feed active.';
if ($src === 'aisstream') $label = 'AISStream optional feed active.';

echo json_encode([
    'configured' => !empty($status['configured']),
    'ok' => !empty($status['ok']),
    'error' => $status['error'] ?? null,
    'vesselCount' => $status['vesselCount'] ?? 0,
    'updatedAt' => $status['updatedAt'] ?? null,
    'activeSource' => $src,
    'primary' => $status['primary'] ?? 'digitraffic+norway',
    'norwayConnected' => !empty($status['norwayConnected']),
    'coverage' => $status['coverage'] ?? $label,
    'source' => $label,
]);
