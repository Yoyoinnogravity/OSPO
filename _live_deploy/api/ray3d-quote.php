<?php
// 3D ray-tracing GPU job quote request (does not run the model on this host).
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

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
if (!$input || empty($input['email']) || strpos($input['email'], '@') === false) {
    http_response_code(400);
    echo json_encode(['error' => 'A contact email is required']);
    exit;
}

$metricsIn = isset($input['metrics']) && is_array($input['metrics']) ? $input['metrics'] : [];
$apertureM = isset($metricsIn['apertureM']) ? floatval($metricsIn['apertureM']) : 0;
if ($apertureM <= 0) {
    http_response_code(400);
    echo json_encode(['error' => '3D migration aperture (m) is required']);
    exit;
}

$entry = [
    'id' => time() . '_' . rand(1000, 9999),
    'email' => filter_var($input['email'], FILTER_SANITIZE_EMAIL),
    'name' => isset($input['name']) ? htmlspecialchars(strip_tags($input['name']), ENT_QUOTES, 'UTF-8') : '',
    'company' => isset($input['company']) ? htmlspecialchars(strip_tags($input['company']), ENT_QUOTES, 'UTF-8') : '',
    'phone' => isset($input['phone']) ? preg_replace('/[^0-9+\- ()]/', '', $input['phone']) : '',
    'algorithm' => isset($input['algorithm']) ? substr(preg_replace('/[^a-z0-9_\-]/', '', strtolower($input['algorithm'])), 0, 32) : '',
    'quoteUsd' => isset($input['quoteUsd']) ? floatval($input['quoteUsd']) : null,
    'gpuHours' => isset($input['gpuHours']) ? floatval($input['gpuHours']) : null,
    'metrics' => $metricsIn,
    'summary' => isset($input['summary']) ? substr(strip_tags($input['summary']), 0, 4000) : '',
    'requestedAt' => date('c'),
    'ip' => $_SERVER['REMOTE_ADDR'] ?? 'unknown'
];

$dbFile = __DIR__ . '/ray3d_quotes.json';
$db = [];
if (file_exists($dbFile)) {
    $db = json_decode(file_get_contents($dbFile), true) ?: [];
}
$db[] = $entry;
file_put_contents($dbFile, json_encode($db, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));

$quote = $entry['quoteUsd'] !== null ? number_format($entry['quoteUsd'], 0) : 'n/a';
$hours = $entry['gpuHours'] !== null ? number_format($entry['gpuHours'], 2) : 'n/a';
$body = "=== CANDOOKA 3D RAY-TRACE GPU QUOTE ===\n\n";
$body .= "Contact: {$entry['name']} | {$entry['email']} | {$entry['phone']}\n";
$body .= "Company: {$entry['company']}\n";
$body .= "Algorithm: {$entry['algorithm']}\n";
$body .= "3D migration aperture (m): " . number_format($apertureM, 0) . "\n";
$body .= "GPU hours (est.): {$hours}\n";
$body .= "Quote USD: {$quote}\n";
$body .= "Time: {$entry['requestedAt']}\n";
$body .= "IP: {$entry['ip']}\n\n";
$body .= "SUMMARY\n{$entry['summary']}\n\n";
$body .= "METRICS\n" . json_encode($entry['metrics'], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n";

$headers = "From: noreply@candooka.world\r\nReply-To: {$entry['email']}\r\nX-Mailer: Candooka/1.0\r\n";
$emailSent = true;
foreach (['admin@candooka.world', 'aledmorgan@gmail.com'] as $to) {
    if (!mail($to, "3D ray-trace quote: {$entry['email']} (\${$quote})", $body, $headers)) {
        $emailSent = false;
    }
}

echo json_encode(['success' => true, 'emailSent' => $emailSent, 'id' => $entry['id']]);
