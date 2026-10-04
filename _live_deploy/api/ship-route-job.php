<?php
// Commercial passage desk. The browser only hands in an order and polls.
// The route computer (ship-route-run.php) does the NOAA read and the timing.

require __DIR__ . '/ship-route-store.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-store');

function ship_route_spawn($id) {
    $php = PHP_BINARY ?: 'php';
    $script = __DIR__ . '/ship-route-run.php';
    $cmd = escapeshellarg($php) . ' ' . escapeshellarg($script) . ' ' . escapeshellarg($id);
    exec($cmd . ' > /dev/null 2>&1 &');
}

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $id = isset($_GET['id']) ? (string)$_GET['id'] : '';
    $job = ship_route_job_load($id);
    if (!$job) {
        http_response_code(404);
        echo json_encode(['ok' => false, 'error' => 'No passage with that ticket.']);
        exit;
    }
    echo json_encode(ship_route_job_public($job));
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Send the passage with POST, or read a ticket with GET.']);
    exit;
}

$raw = file_get_contents('php://input');
$in = json_decode($raw ?: '', true);
if (!is_array($in)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Send the passage as JSON.']);
    exit;
}

list($job, $err) = ship_route_job_create($in);
if ($err) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => $err]);
    exit;
}

ship_route_spawn($job['id']);
echo json_encode(ship_route_job_public($job));
