import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const app = fs.readFileSync(new URL('../../cloudflare/public/app.js', import.meta.url), 'utf8');
const controller = fs.readFileSync(new URL('../../cloudflare/public/controller-0450.js', import.meta.url), 'utf8');
const eventlog = fs.readFileSync(new URL('../../cloudflare/public/eventlog-0450.js', import.meta.url), 'utf8');
const vinted = fs.readFileSync(new URL('../../cloudflare/public/vinted-background-132.js', import.meta.url), 'utf8');
const ui = fs.readFileSync(new URL('../../cloudflare/public/ui-160.js', import.meta.url), 'utf8');

const line = (source, prefix) => source.split('\n').find(value => value.startsWith(prefix));

test('Safari Load failed is classified as a retryable transport interruption', () => {
  const source = line(app, 'function transportError');
  assert.ok(source, 'transportError helper missing');
  const context = {};
  vm.runInNewContext(`${source}\nthis.result = transportError(new TypeError('Load failed'));`, context);
  assert.equal(context.result.name, 'TransportError');
  assert.equal(context.result.status, 0);
  assert.equal(context.result.retryable, true);
  assert.equal(context.result.transport, true);
  assert.match(context.result.message, /kurz unterbrochen/);
});

test('a long mobile packet series survives one dropped packet without losing its cursor', async () => {
  const retrySource = line(app, 'async function requestWithBackoff');
  assert.ok(retrySource, 'requestWithBackoff helper missing');
  const attempts = new Map();
  const state = {page: 0, items: new Map(Array.from({length: 819}, (_, index) => [`id-${index}`, {}])), retries: 0, paused: false};
  const context = {
    stopRequested: false,
    window: {gpEventLog() {}},
    workerState() {},
    persist: async () => {},
    countdown: async () => {},
    requestPage: async payload => {
      const count = (attempts.get(payload.page) || 0) + 1;
      attempts.set(payload.page, count);
      if (payload.page === 28 && count === 1) {
        const error = new Error('Verbindung zum Worker kurz unterbrochen.');
        error.status = 0;
        error.retryable = true;
        error.transport = true;
        throw error;
      }
      return {page: payload.page};
    }
  };
  vm.runInNewContext(retrySource, context);
  for (let page = 0; page < 30; page += 1) {
    state.page = page;
    const result = await context.requestWithBackoff({page}, state);
    assert.equal(result.page, page);
  }
  assert.equal(attempts.get(28), 2);
  assert.equal(state.retries, 1);
  assert.equal(state.items.size, 819);
});

test('same-page continuation preserves transient eBay results while durable storage excludes them', () => {
  assert.match(app, /sourceOf\(item\)!=='ebay'/);
  assert.match(app, /activeState&&\(activeState\.paused\|\|activeState\.stopped\)&&activeState\.continuationToken/);
  assert.match(controller, /activeState && \(activeState\.paused \|\| activeState\.stopped\) && activeState\.continuationToken/);
  assert.match(app, /Treffer bleiben auf dieser geöffneten Seite erhalten/);
});

test('background details yield to the primary search and counters use one denominator', () => {
  assert.match(vinted, /window\.GP_SEARCH_RUNNING === true/);
  assert.match(vinted, /gp-search-run-state/);
  assert.match(vinted, /\$\{full\}\/\$\{seen\.size\} vollständig/);
  assert.doesNotMatch(vinted, /\$\{done\}\/\$\{totalQueued\} Hintergrundtreffer geprüft/);
});

test('source progress counts unique listing keys instead of raw repeated rows', () => {
  assert.match(app, /listingKeys:listings\.map\(item=>item\.id\)/);
  assert.match(ui, /for \(const key of listingKeys\) if \(key\) keys\.add\(String\(key\)\)/);
  assert.match(ui, /count: listingKeys \? keys\.size/);
});

test('automatic transport recovery is visible in the search event log', () => {
  assert.match(eventlog, /transport_retry_wait: \['Verbindung wird wiederhergestellt'/);
  assert.match(eventlog, /search\|fetch\|parse\|resume\|transport/);
});
