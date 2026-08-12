import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../../cloudflare/public/eventlog-187.js', import.meta.url), 'utf8');

function boot({stored, identity = {version: '1.8.7', buildId: 'gp-187-20260812-1', eventLogKey: 'gp-log'}} = {}) {
  const clicks = [];
  const revoked = [];
  const anchor = {href: '', download: '', click() { clicks.push({href: this.href, download: this.download}); }, remove() {}};
  const button = {textContent: 'Log herunterladen', listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; }};
  const context = {
    Array, String, JSON, Date, Error, Object,
    Blob: class { constructor(parts, options) { this.parts = parts; this.type = options?.type; } },
    URL: {createObjectURL: () => 'blob:log', revokeObjectURL: url => revoked.push(url)},
    setTimeout: fn => fn(),
    localStorage: {getItem: key => (key === (identity.eventLogKey || 'generic-parser-eventlog') ? stored : null)},
    document: {
      readyState: 'complete',
      getElementById: id => (id === 'download-log' ? button : null),
      createElement: () => anchor,
      body: {append() {}},
      addEventListener() {}
    },
    window: {GP_BUILD_IDENTITY: identity}
  };
  context.globalThis = context;
  vm.runInNewContext(source, context, {filename: 'eventlog-187.js'});
  return {api: context.window.GPEventLogExport, button, clicks, revoked};
}

test('the export carries the release identity so a log can be placed later', () => {
  const {api} = boot({stored: JSON.stringify([{type: 'a'}, {type: 'b'}])});
  const payload = api.exportPayload('2026-08-12T19:30:00.000Z');
  assert.equal(payload.version, '1.8.7');
  assert.equal(payload.build_id, 'gp-187-20260812-1');
  assert.equal(payload.entry_count, 2);
  assert.equal(payload.entries.length, 2);
});

test('a corrupt or missing store yields an empty log instead of throwing', () => {
  // Längenvergleich statt deepEqual: die Arrays entstehen im vm-Realm und
  // tragen dessen Prototyp, was assert/strict als Unterschied wertet.
  assert.equal(boot({stored: 'kein json'}).api.entries().length, 0);
  assert.equal(boot({stored: null}).api.entries().length, 0);
  assert.equal(boot({stored: '{"kein":"array"}'}).api.entries().length, 0);
});

test('the file name avoids characters Windows rejects', () => {
  const {api} = boot({stored: '[]'});
  const name = api.fileName('2026-08-12T19:30:00.000Z');
  assert.match(name, /^genericparser-log-1\.8\.7-2026-08-12T19-30-00-000Z\.json$/);
  assert.ok(!name.includes(':'));
});

test('a click downloads the log and releases the blob afterwards', () => {
  const {button, clicks, revoked} = boot({stored: JSON.stringify([{type: 'a'}])});
  button.listeners.click({currentTarget: button});
  assert.equal(clicks.length, 1);
  assert.equal(clicks[0].href, 'blob:log');
  assert.match(clicks[0].download, /^genericparser-log-1\.8\.7-/);
  // Ohne Freigabe bliebe der Blob für die Lebensdauer des Dokuments im Speicher.
  assert.deepEqual(revoked, ['blob:log']);
});

test('an empty log reports that instead of writing an empty file', () => {
  const {button, clicks} = boot({stored: '[]'});
  const captured = [];
  Object.defineProperty(button, 'textContent', {get: () => captured.at(-1) || '', set: v => captured.push(v)});
  button.listeners.click({currentTarget: button});
  assert.equal(clicks.length, 0);
  assert.ok(captured.includes('Log ist leer'));
});

test('a page without the button installs nothing and stays silent', () => {
  const context = {
    Array, String, JSON, Date, Object,
    document: {readyState: 'complete', getElementById: () => null, addEventListener() {}},
    window: {},
    localStorage: {getItem: () => null},
    setTimeout: fn => fn()
  };
  context.globalThis = context;
  vm.runInNewContext(source, context, {filename: 'eventlog-187.js'});
  assert.equal(typeof context.window.GPEventLogExport.download, 'function');
});
