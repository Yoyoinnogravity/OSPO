<?php
require_once __DIR__ . '/_users_lib.php';
candookaCorsJson();

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Method not allowed']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);
if (!is_array($input)) $input = $_POST;

$user = trim((string)($input['user'] ?? $input['username'] ?? $input['email'] ?? ''));
$password = (string)($input['password'] ?? $input['pass'] ?? '');

if ($user === '' || $password === '') {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Username and password required']);
    exit;
}

$found = candookaFindUser($user, $password);
if (!$found) {
    http_response_code(401);
    echo json_encode(['ok' => false, 'error' => 'Invalid account or password']);
    exit;
}

echo json_encode([
    'ok' => true,
    'confirmed' => true,
    'source' => 'server',
    'user' => candookaPublicUser($found),
]);
