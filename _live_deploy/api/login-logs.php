<?php
require_once __DIR__ . '/_users_lib.php';
candookaCorsJson();

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

$path = candookaDataDir() . '/login-logs.json';
$fallback = __DIR__ . '/login-logs.json';
$data = candookaReadJsonFile($path) ?: candookaReadJsonFile($fallback);
$logs = [];
if (is_array($data)) {
    $logs = isset($data['logs']) && is_array($data['logs']) ? $data['logs'] : (isset($data[0]) ? $data : []);
}
if (!is_array($logs)) $logs = [];

echo json_encode(['logs' => array_reverse($logs), 'count' => count($logs)]);
