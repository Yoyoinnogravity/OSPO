/**
 * Guards the Admin Login unlock rules in app.js.
 * Run: node _live_deploy/test-admin-login.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const dir = dirname(fileURLToPath(import.meta.url));
const js = readFileSync(join(dir, 'app.js'), 'utf8');
const html = readFileSync(join(dir, 'index.html'), 'utf8');

const begin = js.indexOf('// --- admin-login-helpers begin ---');
const end = js.indexOf('// --- admin-login-helpers end ---');
assert.ok(begin >= 0 && end > begin, 'helper markers missing from app.js');

const ADMIN_PASSWORD = 'candooka2024';
const slice = js.slice(begin, end);
const helpers = new Function(
  'ADMIN_PASSWORD',
  `${slice}\nreturn { isAdminishUser, isAdminPanelPassword, ADMIN_UNLOCK_PINS, OWNER_USERNAMES, OWNER_EMAILS };`
)(ADMIN_PASSWORD);

const { isAdminishUser, isAdminPanelPassword, ADMIN_UNLOCK_PINS } = helpers;

assert.deepEqual(ADMIN_UNLOCK_PINS, ['1234', '9999']);
assert.equal(isAdminPanelPassword('candooka2024'), true);
assert.equal(isAdminPanelPassword('  candooka2024  '), true);
assert.equal(isAdminPanelPassword('1234'), true);
assert.equal(isAdminPanelPassword('  1234\n'), true);
assert.equal(isAdminPanelPassword('9999'), true);
assert.equal(isAdminPanelPassword(''), false);
assert.equal(isAdminPanelPassword('   '), false);
assert.equal(isAdminPanelPassword('wrong'), false);
assert.equal(isAdminPanelPassword('Kite4677!'), false);

assert.equal(isAdminishUser({ name: 'Aled', role: 'operator' }), true, 'site owner Aled must unlock admin');
assert.equal(isAdminishUser({ name: 'admin', role: 'Admin' }), true);
assert.equal(isAdminishUser({ email: 'admin@candooka.world', role: 'Viewer' }), true);
assert.equal(isAdminishUser({ email: 'aledmorgan@gmail.com', role: 'operator' }), true);
assert.equal(isAdminishUser({ name: 'kite', role: 'admin' }), true);
assert.equal(isAdminishUser({ name: 'patric', role: 'Senior Surveyor' }), true);
assert.equal(isAdminishUser({ name: 'GUEST', role: 'Viewer' }), false);
assert.equal(isAdminishUser({ name: 'demouser', role: 'Viewer' }), false);
assert.equal(isAdminishUser({ name: 'MURAT', role: 'operator' }), false);
assert.equal(isAdminishUser({}, 'Aled'), true);
assert.equal(isAdminishUser({}, 'admin@candooka.world'), true);

assert.match(js, /async function adminLogin\s*\(/);
assert.match(js, /isAdminPanelPassword\(pw\)/);
assert.match(js, /function completeAdminLogin\s*\(/);
assert.doesNotMatch(
  js,
  /Fail-safe:[\s\S]{0,120}if \(pw === ADMIN_PASSWORD\)/,
  'adminLogin must not only compare the master password'
);

assert.match(html, /app\.js\?v=17\.29/);
assert.match(html, /onkeydown="if\(event\.key==='Enter'\)\{event\.preventDefault\(\);adminLogin\(\);\}"/);
assert.match(html, /event\.preventDefault\(\); showAdminLogin\(\)/);

console.log('test-admin-login.mjs: ok');
