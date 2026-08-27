<?php
require_once __DIR__ . '/_users_lib.php';
candookaCorsJson();

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'GET') {
    $key = $_GET['key'] ?? '';
    $store = candookaLoadStore();
    $users = candookaMergeBuiltins($store['users']);
    $admin = candookaAdminKeyOk($key);
    $outUsers = [];
    foreach ($users as $u) {
        if ($admin) {
            $outUsers[] = $u;
        } else {
            $pub = candookaPublicUser($u);
            if ($pub) $outUsers[] = $pub;
        }
    }
    $payload = [
        'users' => $outUsers,
        'updated' => $store['updated'],
        'source' => 'server',
    ];
    if (!$admin) $payload['count'] = count($outUsers);
    echo json_encode($payload);
    exit;
}

if ($method !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Method not allowed']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);
if (!is_array($input) || !isset($input['users']) || !is_array($input['users'])) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Invalid payload']);
    exit;
}

$key = $input['key'] ?? $_GET['key'] ?? '';
if (!candookaAdminKeyOk($key)) {
    http_response_code(403);
    echo json_encode(['ok' => false, 'error' => 'Invalid admin key']);
    exit;
}

$result = candookaSaveUsers($input['users']);
if (empty($result['ok'])) {
    http_response_code(500);
    echo json_encode($result);
    exit;
}

echo json_encode([
    'ok' => true,
    'count' => $result['count'],
    'updated' => $result['updated'],
]);
