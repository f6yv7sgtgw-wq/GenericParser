import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../../cloudflare/public/vinted-background-132.js', import.meta.url), 'utf8');

function listing(index) {
  return {id: `vinted:${index}`, source: 'vinted', url: `https://www.vinted.de/items/${index}`, title: `Artikel ${index}`};
}

// Boots the background enrichment IIFE against stubbed browser globals and
// returns the handles a test needs to drive and observe one run.
function boot({listings, searchRunning = false, delayMs = 25} = {}) {
  const state = {inFlight: 0, maxInFlight: 0, requests: 0, sent: []};
  const context = {
    console,
    Map,
    Set,
    JSON,
    Math,
    Promise,
    Array,
    Number,
    String,
    Boolean,
    DOMException,
    AbortController,
    setTimeout,
    clearTimeout,
    performance,
    stopRequested: false,
    sleep: ms => new Promise(resolve => setTimeout(resolve, ms)),
    apiUrl: path => path,
    headers: () => ({}),
    // No detail panel in the harness: renderProgress leaves early on null.
    document: {getElementById: () => null, addEventListener() {}},
    window: {
      GP_CONTROLLER_IDENTITY: {version: 'test'},
      GP_SEARCH_RUNNING: searchRunning,
      gpEventLog() {},
      addEventListener() {}
    },
    renderState() {},
    requestPage: async () => ({listings}),
    async fetch(url, options) {
      const body = JSON.parse(options.body);
      state.sent.push(body.listings.map(item => item.id));
      state.inFlight += 1;
      state.maxInFlight = Math.max(state.maxInFlight, state.inFlight);
      await new Promise(resolve => setTimeout(resolve, delayMs));
      state.inFlight -= 1;
      state.requests += 1;
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify({
          listings: body.listings.map(item => ({...item, image_url: 'bild', price: 5, description: 'text'}))
        })
      };
    }
  };
  context.globalThis = context;
  vm.runInNewContext(source, context, {filename: 'vinted-background-132.js'});
  return {context, state};
}

const settle = async (ms = 400) => new Promise(resolve => setTimeout(resolve, ms));

test('two detail batches are in flight at the same time', async () => {
  const items = Array.from({length: 6}, (_, index) => listing(index));
  const {context, state} = boot({listings: items});

  await context.requestPage({query: 'King Louie', page: 0}, {});
  await settle();

  assert.equal(state.requests, 2, 'six listings must become two batches of three');
  assert.equal(state.maxInFlight, 2, 'both batches must overlap instead of running one after another');
  assert.deepEqual(state.sent.flat().sort(), items.map(item => item.id).sort());
});

test('every queued listing is requested exactly once across parallel workers', async () => {
  const items = Array.from({length: 11}, (_, index) => listing(index));
  const {context, state} = boot({listings: items, delayMs: 5});

  await context.requestPage({query: 'King Louie', page: 0}, {});
  await settle();

  const sent = state.sent.flat();
  assert.equal(sent.length, items.length);
  assert.equal(new Set(sent).size, items.length, 'no listing may be enriched twice');
  assert.equal(state.requests, 4, 'eleven listings are three full batches plus a remainder');
});

test('a running primary search still blocks every worker, not just the first', async () => {
  const items = Array.from({length: 9}, (_, index) => listing(index));
  const {context, state} = boot({listings: items, searchRunning: true});

  await context.requestPage({query: 'King Louie', page: 0}, {});
  await settle();

  assert.equal(state.requests, 0, 'background details must yield to the primary packet stream');
});
