import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const controller = fs.readFileSync(new URL('../../cloudflare/public/controller-0450.js', import.meta.url), 'utf8');
const app = fs.readFileSync(new URL('../../cloudflare/public/app.js', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../../cloudflare/public/ui-161.css', import.meta.url), 'utf8');
const serviceWorker = fs.readFileSync(new URL('../../cloudflare/public/service-worker.js', import.meta.url), 'utf8');

test('runtime controller forwards the v2 search state through every wrapper', () => {
  assert.match(controller, /requestPage = async function\(payload, state\)/);
  assert.match(controller, /originalRequestPage\(payload, state\)/);
  assert.match(controller, /requestPage\(payload, s\)/);
  assert.doesNotMatch(controller, /originalRequestPage\(payload\);/);
  assert.doesNotMatch(controller, /return await requestPage\(payload\);/);
});

test('v2 browser request remains bound to batch and continuation state', () => {
  assert.match(app, /batch_id:state\.batchId/);
  assert.match(app, /continuation_token:state\.continuationToken\|\|null/);
  assert.match(app, /requestWithBackoff\(\{\.\.\.s\.base,page:requestedPage,source:s\.source\},s\)/);
});

test('browser storage cleanup is fail-open and the hotfix cache is isolated', () => {
  assert.match(app, /Gespeicherter Suchstand konnte nicht gelöscht werden/);
  assert.match(app, /service-worker\.js\?v=gp-162/);
  assert.match(serviceWorker, /generic-parser-mobile-gp-162/);
  assert.match(serviceWorker, /\.\/ui-161\.css/);
});

test('friendly palette keeps dark-mode contrast with teal and warm accents', () => {
  assert.match(css, /--bg: #0b1d29/);
  assert.match(css, /--accent: #70d7d2/);
  assert.match(css, /--yellow: #f5cf76/);
  assert.match(css, /--text: #f5fbfc/);
});
