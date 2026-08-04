'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const baseSource = fs.readFileSync(path.join(root, 'cloudflare/public/auto-resume-04462.js'), 'utf8');
const wrapperSource = fs.readFileSync(path.join(root, 'cloudflare/public/auto-resume-04466.js'), 'utf8');

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
    autoResume: {
      quietPeriodMs: 120000,
      healthIntervalMs: 15000,
      maxHealthChecks: 4,
      maxAutoResumes: 1,
      controlRetryMs: 10000,
    },
  },
  gpEventLog() {},
};
global.location = {href: 'https://example.invalid/'};
global.fetch = async () => ({ok: true, text: async () => baseSource});

vm.runInThisContext(wrapperSource, {filename: 'auto-resume-04466.js'});

setTimeout(() => {
  assert.ok(generatedSource, 'recovery runtime was not generated');
  assert.match(generatedSource, /generic-parser-auto-resume-044661/);
  assert.match(generatedSource, /button\.classList\.remove\('hidden'\)/);
  assert.match(generatedSource, /button\.disabled = false/);
  assert.match(generatedSource, /auto_resume_control_retry/);
  assert.match(generatedSource, /resume_control_failed_after_retry/);
  assert.match(generatedSource, /event\.type === 'search_resume'/);
  assert.doesNotMatch(generatedSource, /const RECOVERY_KEY = 'generic-parser-auto-resume-04462'/);
  console.log('0.44.6.6.1 recovery-control runtime compiles');
}, 25);
