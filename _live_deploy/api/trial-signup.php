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

$email = filter_var($input['email'] ?? '', FILTER_SANITIZE_EMAIL);
if (!$email || strpos($email, '@') === false) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Valid email required']);
    exit;
}

$entry = [
    'email' => $email,
    'phone' => substr(preg_replace('/[^0-9+\- ()]/', '', (string)($input['phone'] ?? '')), 0, 40),
    'name' => substr(strip_tags((string)($input['name'] ?? '')), 0, 120),
    'requestedAt' => $input['requestedAt'] ?? gmdate('c'),
    'ip' => $_SERVER['REMOTE_ADDR'] ?? '',
];
candookaAppendLog('trial-signups.json', $entry);

$users = candookaLoadUsers();
$exists = false;
foreach ($users as $u) {
    if (strtolower($u['email'] ?? '') === strtolower($email)) { $exists = true; break; }
}
if (!$exists) {
    $users[] = [
        'id' => time(),
        'name' => $entry['name'] !== '' ? $entry['name'] : explode('@', $email)[0],
        'email' => $email,
        'phone' => $entry['phone'],
        'role' => 'Trial (1 Month)',
        'password' => CANDOOKA_GUEST_PASS,
        'validFrom' => gmdate('c'),
        'validTo' => gmdate('c', time() + 30 * 86400),
        'addedAt' => gmdate('c'),
    ];
    candookaSaveUsers($users);
}

$body = "New Candooka trial request\n\nName: {$entry['name']}\nEmail: {$email}\nPhone: {$entry['phone']}\nTime: {$entry['requestedAt']}\n";
$headers = "From: noreply@candooka.world\r\nReply-To: {$email}\r\nX-Mailer: Candooka/1.0\r\n";
foreach (['admin@candooka.world', 'aledmorgan@gmail.com'] as $to) {
    @mail($to, "Candooka trial: {$email}", $body, $headers);
}

echo json_encode(['ok' => true]);
