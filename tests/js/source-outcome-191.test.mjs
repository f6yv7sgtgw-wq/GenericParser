import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// 1.9.1: Eine Quelle, die mitten im Lauf natürlich endet, bekommt ihren
// eigenen Endgrund. Vorher erbte sie den Paket-Stop-Grund
// `packet_budget_reached` — das erfundene "Kleinanzeigen-Paketbudget".

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

const packet = (source, {listings = 25, complete = false, status = 'ok', reason = null, sourceComplete = false} = {}) => ({
  pagination: {source, complete, next_page: complete ? null : 1, stop_reason: complete ? 'batch_complete' : 'packet_budget_reached'},
  listings: Array.from({length: listings}, () => ({})),
  source_status: [{source, status, reason, source_complete: sourceComplete}]
});

test('a source finishing mid-run gets its own end, not the packet stop reason', () => {
  const logged = [];
  const {recordSourceOutcome} = api(logged);
  const state = {source: 'auto'};
  recordSourceOutcome(state, packet('kleinanzeigen', {listings: 7}));
  recordSourceOutcome(state, packet('kleinanzeigen', {listings: 4, sourceComplete: true}));
  recordSourceOutcome(state, packet('ebay'));

  const outcome = state.sourceOutcomes.kleinanzeigen;
  assert.equal(outcome.ended, true);
  assert.equal(outcome.reason, 'source_complete');
  assert.equal(state.sourceOutcomes.ebay.ended, false);
  assert.deepEqual(logged, [{
    type: 'source_finished', source: 'kleinanzeigen', status: 'ok',
    reason: 'source_complete', packets: 2, listings: 11
  }]);
});

test('a healthy mid-run packet no longer inherits packet_budget_reached', () => {
  const {recordSourceOutcome} = api();
  const state = {source: 'auto'};
  recordSourceOutcome(state, packet('kleinanzeigen', {listings: 7}));
  assert.equal(state.sourceOutcomes.kleinanzeigen.ended, false);
  assert.equal(state.sourceOutcomes.kleinanzeigen.reason, '');
});

test('a blocked source keeps its real reason over the generic completion', () => {
  const {recordSourceOutcome} = api();
  const state = {source: 'auto'};
  recordSourceOutcome(state, packet('vinted', {status: 'blocked', reason: 'vinted_session_bootstrap_access_limited', sourceComplete: true}));
  assert.equal(state.sourceOutcomes.vinted.reason, 'vinted_session_bootstrap_access_limited');
  assert.equal(state.sourceOutcomes.vinted.status, 'blocked');
});

test('the batch end still closes the last running source', () => {
  const {recordSourceOutcome} = api();
  const state = {source: 'auto'};
  recordSourceOutcome(state, packet('ebay'));
  recordSourceOutcome(state, packet('ebay', {complete: true, sourceComplete: true}));
  const outcome = state.sourceOutcomes.ebay;
  assert.equal(outcome.ended, true);
  assert.equal(outcome.reason, 'source_complete');
});
