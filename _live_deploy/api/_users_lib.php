<?php
/**
 * Shared user-store helpers for Candooka logins.
 * Keep the live account file out of the public api/ folder when possible.
 */
if (basename($_SERVER['SCRIPT_FILENAME'] ?? '') === basename(__FILE__)) {
    http_response_code(403);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'Forbidden']);
    exit;
}

const CANDOOKA_ADMIN_KEY = 'candooka2024';
const CANDOOKA_GUEST_USER = 'GUEST';
const CANDOOKA_GUEST_PASS = 'candooka-ospo';

function candookaCorsJson() {
    header('Content-Type: application/json');
    header('Cache-Control: no-store');
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
}

function candookaDataDir() {
    $candidates = [
        '/var/www/candooka/data',
        dirname(__DIR__) . '/data',
        __DIR__,
    ];
    foreach ($candidates as $dir) {
        if (is_dir($dir) && is_writable($dir)) return $dir;
    }
    foreach ($candidates as $dir) {
        if (is_dir($dir)) return $dir;
    }
    return __DIR__;
}

function candookaUsersPaths() {
    $data = candookaDataDir();
    return [
        $data . '/users-db.json',
        __DIR__ . '/users-db.json',
    ];
}

function candookaBuiltinUsers() {
    return [
        [
            'id' => 'admin',
            'name' => 'admin',
            'email' => 'admin@candooka.world',
            'phone' => '',
            'role' => 'Admin',
            'password' => CANDOOKA_ADMIN_KEY,
            'validFrom' => null,
            'validTo' => null,
            'addedAt' => '2024-01-01T00:00:00Z',
            'builtin' => true,
        ],
        [
            'id' => 'guest',
            'name' => CANDOOKA_GUEST_USER,
            'email' => 'guest@candooka.world',
            'phone' => '',
            'role' => 'Viewer',
            'password' => CANDOOKA_GUEST_PASS,
            'validFrom' => null,
            'validTo' => null,
            'addedAt' => '2024-01-01T00:00:00Z',
            'builtin' => true,
        ],
    ];
}

function candookaUserKey($user) {
    $name = strtolower(trim((string)($user['name'] ?? '')));
    $email = strtolower(trim((string)($user['email'] ?? '')));
    return $name !== '' ? $name : $email;
}

function candookaMergeBuiltins($users) {
    if (!is_array($users)) $users = [];
    $byKey = [];
    foreach ($users as $u) {
        if (!is_array($u)) continue;
        $key = candookaUserKey($u);
        if ($key === '') continue;
        $byKey[$key] = $u;
    }
    foreach (candookaBuiltinUsers() as $built) {
        $key = candookaUserKey($built);
        if (!isset($byKey[$key])) {
            $byKey[$key] = $built;
        } else {
            // Keep stored row but never lose the well-known password if it was wiped.
            if (empty($byKey[$key]['password'])) {
                $byKey[$key]['password'] = $built['password'];
            }
            if (empty($byKey[$key]['role'])) {
                $byKey[$key]['role'] = $built['role'];
            }
        }
    }
    return array_values($byKey);
}

function candookaReadJsonFile($path) {
    if (!$path || !is_file($path) || !is_readable($path)) return null;
    $raw = @file_get_contents($path);
    if ($raw === false || trim($raw) === '') return null;
    // A Git LFS pointer is not a user database — treat as missing.
    if (strncmp($raw, 'version https://git-lfs.github.com', 34) === 0) return null;
    $data = json_decode($raw, true);
    return is_array($data) ? $data : null;
}

function candookaAtomicWrite($path, $contents) {
    $dir = dirname($path);
    if (!is_dir($dir)) {
        @mkdir($dir, 0775, true);
    }
    if (!is_dir($dir) || !is_writable($dir)) return false;

    $tmp = $dir . '/.' . basename($path) . '.' . bin2hex(random_bytes(4)) . '.tmp';
    $ok = @file_put_contents($tmp, $contents, LOCK_EX);
    if ($ok === false) {
        @unlink($tmp);
        return false;
    }
    if (!@rename($tmp, $path)) {
        @unlink($tmp);
        return false;
    }
    @chmod($path, 0660);
    return true;
}

function candookaBackupFile($path) {
    if (!is_file($path) || filesize($path) <= 2) return;
    $bak = $path . '.bak';
    @copy($path, $bak);
    $stamp = $path . '.' . gmdate('Ymd-His') . '.bak';
    @copy($path, $stamp);
}

function candookaLoadStore() {
    $paths = candookaUsersPaths();
    foreach ($paths as $path) {
        $data = candookaReadJsonFile($path);
        if (!$data) continue;
        $users = isset($data['users']) && is_array($data['users']) ? $data['users'] : (array_keys($data) === range(0, count($data) - 1) ? $data : []);
        if (!is_array($users)) $users = [];
        return [
            'users' => $users,
            'updated' => $data['updated'] ?? null,
            'path' => $path,
        ];
    }
    return ['users' => [], 'updated' => null, 'path' => $paths[0]];
}

function candookaLoadUsers() {
    $store = candookaLoadStore();
    return candookaMergeBuiltins($store['users']);
}

function candookaSaveUsers($users) {
    $users = candookaMergeBuiltins($users);
    if (count($users) === 0) {
        return ['ok' => false, 'error' => 'Refusing to save an empty user list'];
    }

    $existing = candookaLoadStore();
    $existingCount = 0;
    foreach ($existing['users'] as $u) {
        if (is_array($u) && candookaUserKey($u) !== '') $existingCount++;
    }
    // Never replace a populated DB with a list that has no real (non-builtin) users
    // if the incoming payload is empty of everything — mergeBuiltins always adds 2.
    $payload = [
        'updated' => gmdate('c'),
        'users' => array_values($users),
    ];
    $json = json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    if ($json === false) {
        return ['ok' => false, 'error' => 'Could not encode user list'];
    }

    $paths = candookaUsersPaths();
    $written = null;
    foreach ($paths as $path) {
        candookaBackupFile($path);
        if (candookaAtomicWrite($path, $json)) {
            $written = $path;
            break;
        }
    }
    if (!$written) {
        return ['ok' => false, 'error' => 'Write failed — check permissions on users-db.json'];
    }
    return [
        'ok' => true,
        'count' => count($users),
        'updated' => $payload['updated'],
        'path' => $written,
    ];
}

function candookaPublicUser($user) {
    if (!is_array($user)) return null;
    return [
        'id' => $user['id'] ?? $user['name'] ?? '',
        'name' => $user['name'] ?? '',
        'email' => $user['email'] ?? '',
        'phone' => $user['phone'] ?? '',
        'role' => $user['role'] ?? 'Viewer',
        'validFrom' => $user['validFrom'] ?? null,
        'validTo' => $user['validTo'] ?? null,
        'addedAt' => $user['addedAt'] ?? null,
    ];
}

function candookaDatesOk($user) {
    $now = time();
    $from = $user['validFrom'] ?? null;
    $to = $user['validTo'] ?? null;
    if ($from) {
        $ts = strtotime($from);
        if ($ts && $now < $ts) return false;
    }
    if ($to) {
        $ts = strtotime($to);
        if ($ts && $now > $ts + 86400) return false;
    }
    return true;
}

function candookaFindUser($identity, $password) {
    $id = strtolower(trim((string)$identity));
    $pass = (string)$password;
    if ($id === '' || $pass === '') return null;
    foreach (candookaLoadUsers() as $user) {
        $name = strtolower(trim((string)($user['name'] ?? '')));
        $email = strtolower(trim((string)($user['email'] ?? '')));
        if ($id !== $name && $id !== $email) continue;
        if ((string)($user['password'] ?? '') !== $pass) continue;
        if (!candookaDatesOk($user)) continue;
        return $user;
    }
    return null;
}

function candookaAdminKeyOk($key) {
    return is_string($key) && hash_equals(CANDOOKA_ADMIN_KEY, $key);
}

function candookaAppendLog($fileName, $entry) {
    $path = candookaDataDir() . '/' . $fileName;
    $data = candookaReadJsonFile($path);
    $list = [];
    if (is_array($data)) {
        $list = isset($data['logs']) && is_array($data['logs']) ? $data['logs'] : $data;
        if (!is_array($list) || isset($list['logs'])) $list = [];
    }
    $list[] = $entry;
    if (count($list) > 500) {
        $list = array_slice($list, -500);
    }
    $json = json_encode(['logs' => $list, 'count' => count($list), 'updated' => gmdate('c')], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    candookaAtomicWrite($path, $json);
    return $list;
}
