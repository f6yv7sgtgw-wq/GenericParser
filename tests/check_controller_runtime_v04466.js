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
  // Compile without executing the generated browser controller.
  NativeFunction(...args);
  return () => {};
};

global.window = {
  GP_BUILD_IDENTITY: {
    version: '0.44.6.6',
    buildId: 'gp-04466-20260804-1',
    apiContract: 'match-v6.11.7-rollback-04465-cooldown-test',
    eventLogKey: 'generic-parser-eventlog-04466',
    testCooldown: {threshold: 120, durationMs: 90000},
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
  assert.ok(generatedSource, 'runtime controller was not generated');
  assert.match(generatedSource, /const TEST_COOLDOWN_THRESHOLD = 120;/);
  assert.match(generatedSource, /const TEST_COOLDOWN_MS = 90000;/);
  assert.match(generatedSource, /cooldown_threshold_reached/);
  assert.match(generatedSource, /cooldown_start/);
  assert.match(generatedSource, /cooldown_resume/);
  assert.doesNotMatch(generatedSource, /I\.testCooldown/);
  assert.match(generatedSource, /const PACKET|requestWithBackoff|runSearch/);
  console.log('0.44.6.6 generated controller runtime compiles');
}, 25);
