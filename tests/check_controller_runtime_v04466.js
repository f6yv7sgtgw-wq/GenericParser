'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const baseSource = fs.readFileSync(path.join(root, 'cloudflare/public/controller-0411.js'), 'utf8');
const wrapperSource = fs.readFileSync(path.join(root, 'cloudflare/public/controller-04466.js'), 'utf8');

let generatedSource = null;
const NativeFunction = global.Function;

global.Function = function checkedFunction(...args) {
  generatedSource = String(args.at(-1) || '');
  NativeFunction(...args);
  return () => {};
};

global.window = {
  GP_BUILD_IDENTITY: {
    version: '0.44.6.6.1',
    buildId: 'gp-044661-20260805-1',
    apiContract: 'match-v6.11.8-rollback-04465-cooldown120-recovery-control',
    eventLogKey: 'generic-parser-eventlog-044661',
  },
  GP_COOLDOWN_IDENTITY: {
    buildId: 'gp-044661-20260805-1',
    reference: '0.44.6.5',
  },
  GP_HANDSHAKE_READY: false,
  dispatchEvent() {},
};
global.location = {href: 'https://example.invalid/'};
global.document = {getElementById() { return null; }};
global.CustomEvent = class CustomEvent { constructor(type, options) { this.type = type; this.detail = options?.detail; } };
global.fetch = async () => ({ok: true, text: async () => baseSource});

vm.runInThisContext(wrapperSource, {filename: 'controller-04466.js'});

setTimeout(() => {
  assert.ok(generatedSource, 'reference controller was not generated');
  assert.match(generatedSource, /const VERSION = '0\.44\.6\.6\.1';/);
  assert.match(generatedSource, /const BUILD_ID = 'gp-044661-20260805-1';/);
  assert.match(generatedSource, /const API_CONTRACT = 'match-v6\.11\.8-rollback-04465-cooldown120-recovery-control';/);
  assert.match(generatedSource, /const LOG_KEY = 'generic-parser-eventlog-044661';/);
  assert.match(generatedSource, /runControlled/);
  assert.match(generatedSource, /searchButton\?\.addEventListener/);
  assert.doesNotMatch(generatedSource, /Reference countdown anchor missing/);
  assert.doesNotMatch(generatedSource, /TEST_COOLDOWN/);

  const expected = baseSource
    .replace("const VERSION = '0.41.1';", "const VERSION = '0.44.6.6.1';")
    .replace("const BUILD_ID = 'gp-0411-20260802-1';", "const BUILD_ID = 'gp-044661-20260805-1';")
    .replace("const API_CONTRACT = 'match-v6.1-page-worker';", "const API_CONTRACT = 'match-v6.11.8-rollback-04465-cooldown120-recovery-control';")
    .replace("const LOG_KEY = 'generic-parser-eventlog-0411';", "const LOG_KEY = 'generic-parser-eventlog-044661';");
  assert.ok(generatedSource.startsWith(expected), '0.44.6.6.1 controller differs from the 0.44.6.5 reference flow');
  console.log('0.44.6.6.1 reference controller passed');
}, 25);
