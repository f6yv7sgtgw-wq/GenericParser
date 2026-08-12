import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const identitySource = fs.readFileSync(new URL('../../cloudflare/public/build-identity-0450.js', import.meta.url), 'utf8');
const controllerSource = fs.readFileSync(new URL('../../cloudflare/public/controller-0450.js', import.meta.url), 'utf8');
const serviceWorker = fs.readFileSync(new URL('../../cloudflare/public/service-worker.js', import.meta.url), 'utf8');
const eventlogHtml = fs.readFileSync(new URL('../../cloudflare/public/eventlog.html', import.meta.url), 'utf8');
const eventlogScript = fs.readFileSync(new URL('../../cloudflare/public/eventlog-0450.js', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../../cloudflare/public/ui-162.css', import.meta.url), 'utf8');

class TestCustomEvent {
  constructor(type, init = {}) {
    this.type = type;
    this.detail = init.detail;
  }
}

test('a failed live identity request keeps the embedded release ready', async () => {
  const events = [];
  const window = {
    dispatchEvent(event) { events.push(event); }
  };
  const context = {
    window,
    fetch: async () => { throw new TypeError('Load failed'); },
    console: {warn() {}},
    CustomEvent: TestCustomEvent,
    AbortController,
    encodeURIComponent,
    Promise,
    Date,
    setTimeout(callback) { queueMicrotask(callback); return 1; },
    clearTimeout() {},
    queueMicrotask
  };
  vm.runInNewContext(identitySource, context, {filename: 'build-identity-0450.js'});

  const ready = await window.GP_BUILD_IDENTITY_READY;
  assert.equal(ready.version, '1.6.4');
  assert.equal(ready.buildId, 'gp-164-20260812-1');
  assert.equal(ready.webUiApiContract, 'generic-parser-module-v2');
  assert.equal(ready.identityVerified, false);

  const live = await window.GP_LIVE_IDENTITY_READY;
  assert.equal(live.version, '1.6.4');
  assert.match(live.identityError, /Load failed/);
  assert.equal(window.GP_BUILD_IDENTITY_STATUS.ok, false);
  assert.equal(events.at(-1).type, 'gp-identity-status');
});

test('optional controller diagnostics fail open instead of locking search', async () => {
  assert.match(controllerSource, /const directMode = error =>/);
  assert.match(controllerSource, /window\.GP_HANDSHAKE_READY = true/);
  assert.match(controllerSource, /button\.disabled = false/);
  assert.match(controllerSource, /module: 'browser-direct-fallback'/);
  assert.doesNotMatch(controllerSource, /Live-Suche gesperrt/);
  assert.doesNotMatch(controllerSource, /GP_HANDSHAKE_READY = false/);

  const button = {disabled: true, textContent: 'Controller lädt …'};
  const connection = {innerHTML: '', classList: {add() {}, remove() {}}};
  const state = {className: '', innerHTML: ''};
  const footer = {textContent: ''};
  const identity = {
    version: '1.6.4',
    buildId: 'gp-164-20260812-1',
    apiContract: 'generic-parser-module-v1',
    moduleContract: 'generic-parser-module-v1',
    preferredModuleContract: 'generic-parser-module-v2',
    webUiApiContract: 'generic-parser-module-v2',
    sources: ['kleinanzeigen', 'vinted', 'ebay']
  };
  const window = {
    GP_BUILD_IDENTITY_READY: Promise.resolve(identity),
    dispatchEvent() {}
  };
  const document = {
    title: '',
    querySelectorAll() { return []; },
    querySelector(selector) { return selector === 'footer span' ? footer : null; },
    getElementById(id) {
      return {'search-button': button, connection, 'worker-state-text': state}[id] || null;
    }
  };
  vm.runInNewContext(controllerSource, {
    window,
    document,
    location: {href: 'https://example.test/'},
    fetch: async () => { throw new TypeError('Load failed'); },
    CustomEvent: TestCustomEvent,
    URL,
    Promise,
    console,
    setTimeout(callback) { queueMicrotask(callback); return 1; },
    queueMicrotask
  }, {filename: 'controller-0450.js'});
  for (let attempt = 0; attempt < 20 && !window.GP_CONTROLLER_IDENTITY; attempt += 1) {
    await new Promise(resolve => setImmediate(resolve));
  }
  assert.equal(window.GP_HANDSHAKE_READY, true);
  assert.equal(button.disabled, false);
  assert.equal(button.textContent, 'Live-Suche starten');
  assert.equal(window.GP_CONTROLLER_IDENTITY.module, 'browser-direct-fallback');
  assert.match(state.innerHTML, /Die Suche ist verfügbar/);
});

test('service worker bypasses dynamic JSON and API endpoints', () => {
  assert.match(serviceWorker, /url\.pathname\.startsWith\('\/api\/'\)/);
  assert.match(serviceWorker, /\['\/health', '\/version', '\/diagnostics', '\/search'\]/);
  assert.match(serviceWorker, /if \(event\.request\.method !== 'GET' \|\| isDynamicRequest\(url\)\) return/);
  assert.match(serviceWorker, /if \(isNavigation\) return await caches\.match\('\.\/'\)/);
  assert.match(serviceWorker, /return Response\.error\(\)/);
});

test('diagnostics use the current palette and identify web API v2 clearly', () => {
  assert.match(eventlogHtml, /ui-161\.css/);
  assert.match(eventlogHtml, /ui-162\.css/);
  assert.match(eventlogHtml, /Websuche · API v2/);
  assert.match(eventlogHtml, /id="log-filter"/);
  assert.match(eventlogScript, /web_ui_api_contract/);
  assert.match(eventlogScript, /Kompatibilität/);
  assert.match(eventlogScript, /Ein Diagnosefehler sperrt die Suche nicht mehr/);
  assert.match(css, /\.eventlog-hero/);
  assert.match(css, /\.runtime-grid/);
  assert.match(css, /\.event-card/);
});
