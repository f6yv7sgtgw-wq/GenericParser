'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'cloudflare/public/cooldown-04466.js'), 'utf8');

function createContext(withCountdown = true) {
  let now = 1_000;
  const calls = [];
  const events = [];
  const store = new Map();
  const elements = new Map([
    'query', 'required-terms', 'excluded-terms', 'model-patterns', 'brands',
    'max-price', 'market-value', 'postal-code', 'location-id', 'radius-km',
    'clear-progress'
  ].map(id => [id, {value: id === 'query' ? 'SNES' : '', addEventListener() {}}]));

  const context = {
    console,
    Date: {now: () => now},
    stopRequested: false,
    localStorage: {
      getItem: key => store.get(key) || null,
      setItem: (key, value) => store.set(key, value),
      removeItem: key => store.delete(key),
    },
    document: {getElementById: id => elements.get(id) || null},
    window: null,
  };
  context.window = context;
  context.GP_BUILD_IDENTITY = {
    buildId: 'gp-04466-20260804-3',
    testCooldown: {threshold: 120, durationMs: 90_000},
  };
  context.gpEventLog = (type, message, data) => events.push({type, message, data});
  if (withCountdown) {
    context.countdown = async (ms, page, loaded, label) => {
      calls.push({ms, page, loaded, label});
      now += ms;
    };
  }
  vm.createContext(context);
  vm.runInContext(source, context, {filename: 'cooldown-04466.js'});
  return {context, calls, events};
}

(async () => {
  const {context, calls, events} = createContext(true);
  await context.countdown(5_000, 1, 119, 'Nächste Seite');
  await context.countdown(5_000, 2, 120, 'Nächste Seite');
  await context.countdown(5_000, 3, 127, 'Nächste Seite');
  await context.countdown(5_000, 4, 240, 'Nächste Seite');
  await context.countdown(15_000, 5, 247, 'Retry 1');

  assert.deepEqual(calls.map(call => call.ms), [5_000, 90_000, 5_000, 90_000, 15_000]);
  assert.deepEqual(
    events.filter(event => event.type === 'cooldown_start').map(event => event.data.threshold),
    [120, 240]
  );
  assert.deepEqual(
    events.filter(event => event.type === 'cooldown_resume').map(event => event.data.threshold),
    [120, 240]
  );

  // Fail-open proof: missing cooldown target must not throw or change handshake.
  const failOpen = createContext(false);
  assert.equal(failOpen.context.GP_HANDSHAKE_READY, undefined);
  assert.equal(failOpen.context.GP_COOLDOWN_IDENTITY, undefined);

  console.log('0.44.6.6 Build 3 cooldown runtime passed');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
