'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const identity = fs.readFileSync(path.join(root, 'cloudflare/public/build-identity-0450.js'), 'utf8');
const controller = fs.readFileSync(path.join(root, 'cloudflare/public/controller-0450.js'), 'utf8');
const debug = fs.readFileSync(path.join(root, 'cloudflare/public/module-debug-0450.js'), 'utf8');
const index = fs.readFileSync(path.join(root, 'cloudflare/public/index.html'), 'utf8');

assert.match(identity, /version:'0\.45\.0'/);
assert.match(identity, /buildId:'gp-0450-20260805-1'/);
assert.match(identity, /enabledByDefault:false/);
assert.match(identity, /networkUsed:false/);

assert.match(controller, /controller-0411\.js\?v=0\.450-reference-source/);
assert.doesNotMatch(controller, /cooldown/i);
assert.match(controller, /searchCoreChanged:false/);
assert.match(controller, /controllerFlowChanged:false/);

assert.match(debug, /X-GenericParser-Debug/);
assert.match(debug, /X-GenericParser-Tests/);
assert.match(debug, /Modultests sind deaktiviert/);
assert.match(debug, /if \(!I\) return/);
assert.match(debug, /window\.addEventListener\('gp-controller-ready'/);

const identityPos = index.indexOf('build-identity-0450.js');
const appPos = index.indexOf('app.js?v=0.450');
const controllerPos = index.indexOf('controller-0450.js');
const debugPos = index.indexOf('module-debug-0450.js');
const recoveryPos = index.indexOf('auto-resume-0450.js');
assert.ok(identityPos < appPos && appPos < controllerPos && controllerPos < debugPos && debugPos < recoveryPos);
assert.match(index, /id="debug-logs" type="checkbox"/);
assert.match(index, /id="module-tests" type="checkbox"/);
assert.doesNotMatch(index, /id="debug-logs" type="checkbox" checked/);
assert.doesNotMatch(index, /id="module-tests" type="checkbox" checked/);

console.log('0.45 module browser diagnostics passed');
