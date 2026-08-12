import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const app = fs.readFileSync(new URL('../../cloudflare/public/app.js', import.meta.url), 'utf8');
const line = (prefix) => app.split('\n').find(value => value.startsWith(prefix));

function api(logged = []) {
  const context = {
    Object, Array, String, Number, Boolean,
    window: {gpEventLog: (type, message, data) => logged.push({type, ...data})},
    esc: value => String(value ?? '')
  };
  const source = [
    line('function sourceStatusOf'),
    line('function recordSourceOutcome'),
    line('const SOURCE_END_LABELS'),
    line('function sourceOutcomeMarkup')
  ].join('\n');
  vm.runInNewContext(`${source}\nthis.api = {recordSourceOutcome, sourceOutcomeMarkup};`, context);
  return context.api;
}

const packet = (source, {listings = 25, complete = false, status, reason} = {}) => ({
  pagination: {source, complete, next_page: complete ? null : 1, stop_reason: reason},
  listings: Array.from({length: listings}, () => ({})),
  source_status: status ? [{source, status, reason}] : undefined
});

test('a finished source records why it stopped, not just that it stopped', () => {
  const logged = [];
  const {recordSourceOutcome} = api(logged);
  const state = {source: 'vinted'};
  recordSourceOutcome(state, packet('vinted'));
  recordSourceOutcome(state, packet('vinted', {listings: 10, complete: true, status: 'blocked', reason: 'vinted_browser_access_limited'}));

  const outcome = state.sourceOutcomes.vinted;
  assert.equal(outcome.ended, true);
  assert.equal(outcome.status, 'blocked');
  assert.equal(outcome.reason, 'vinted_browser_access_limited');
  assert.equal(outcome.listings, 35);
  assert.equal(outcome.packets, 2);
  assert.deepEqual(logged, [{
    type: 'source_finished', source: 'vinted', status: 'blocked',
    reason: 'vinted_browser_access_limited', packets: 2, listings: 35
  }]);
});

test('each source is counted on its own while they rotate', () => {
  const {recordSourceOutcome} = api();
  const state = {source: 'auto'};
  recordSourceOutcome(state, packet('kleinanzeigen', {listings: 7}));
  recordSourceOutcome(state, packet('vinted'));
  recordSourceOutcome(state, packet('ebay'));
  recordSourceOutcome(state, packet('kleinanzeigen', {listings: 7}));
  assert.equal(state.sourceOutcomes.kleinanzeigen.listings, 14);
  assert.equal(state.sourceOutcomes.kleinanzeigen.packets, 2);
  assert.equal(state.sourceOutcomes.vinted.listings, 25);
  assert.equal(Object.keys(state.sourceOutcomes).length, 3);
});

test('the end is reported once, not on every further packet', () => {
  const logged = [];
  const {recordSourceOutcome} = api(logged);
  const state = {source: 'ebay'};
  const done = packet('ebay', {complete: true, status: 'ok'});
  recordSourceOutcome(state, done);
  recordSourceOutcome(state, done);
  assert.equal(logged.length, 1);
});

test('the diagnostics line names the source, its verdict and its yield', () => {
  const {recordSourceOutcome, sourceOutcomeMarkup} = api();
  const state = {source: 'auto'};
  recordSourceOutcome(state, packet('vinted', {listings: 110, complete: true, status: 'blocked', reason: 'vinted_browser_access_limited'}));
  recordSourceOutcome(state, packet('ebay'));
  const markup = sourceOutcomeMarkup(state);
  assert.match(markup, /vinted: beendet · von der Quelle blockiert · vinted_browser_access_limited · 110 Treffer/);
  assert.match(markup, /ebay: läuft/);
});

test('without any packet there is nothing to report', () => {
  const {sourceOutcomeMarkup} = api();
  assert.equal(sourceOutcomeMarkup({}), '');
  assert.equal(sourceOutcomeMarkup({sourceOutcomes: {}}), '');
});
