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
    version: '0.44.6.6',
    buildId: 'gp-04466-20260804-2',
    apiContract: 'match-v6.11.7-rollback-04465-cooldown-test',
    eventLogKey: 'generic-parser-eventlog-04466',
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
  assert.match(generatedSource, /const TEST_COOLDOWN_STEP = 120;/);
  assert.match(generatedSource, /const TEST_COOLDOWN_MS = 90000;/);
  assert.match(generatedSource, /generic-parser-cooldown-04466-b2/);
  assert.match(generatedSource, /state\.nextThreshold/);
  assert.match(generatedSource, /completedThresholds/);
  assert.match(generatedSource, /while\(Number\(loaded\|\|0\)>=Number\(state\.nextThreshold/);
  assert.match(generatedSource, /ms=TEST_COOLDOWN_MS/);
  assert.match(generatedSource, /mode:'replace_regular_delay'/);
  assert.match(generatedSource, /cooldown_threshold_reached/);
  assert.match(generatedSource, /cooldown_start/);
  assert.match(generatedSource, /cooldown_resume/);
  assert.doesNotMatch(generatedSource, /testCooldownDone/);
  assert.match(generatedSource, /requestWithBackoff|runSearch/);
  console.log('0.44.6.6 Build 2 repeated cooldown runtime compiles');
}, 25);
