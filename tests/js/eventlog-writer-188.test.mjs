import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../../cloudflare/public/eventlog-writer-188.js', import.meta.url), 'utf8');

function boot({identity = {version: '1.8.8', eventLogKey: 'gp-log'}, failWrites = 0, existing} = {}) {
  const store = new Map();
  let writes = 0;
  const context = {
    Array, String, JSON, Date, Object, Math,
    localStorage: {
      getItem: key => store.get(key) ?? null,
      setItem: (key, value) => {
        writes += 1;
        if (writes <= failWrites) throw new Error('QuotaExceeded');
        store.set(key, value);
      }
    },
    window: {GP_BUILD_IDENTITY: identity, ...(existing ? {gpEventLog: existing} : {})}
  };
  context.globalThis = context;
  vm.runInNewContext(source, context, {filename: 'eventlog-writer-188.js'});
  return {context, store};
}

test('the writer that every caller was checking for now exists', () => {
  const {context, store} = boot();
  assert.equal(typeof context.window.gpEventLog, 'function');
  context.window.gpEventLog('source_finished', 'Quelle vinted beendet', {source: 'vinted', status: 'ok'});
  const entries = JSON.parse(store.get('gp-log'));
  assert.equal(entries.length, 1);
  assert.equal(entries[0].type, 'source_finished');
  assert.equal(entries[0].data.source, 'vinted');
  assert.equal(entries[0].version, '1.8.8');
  assert.ok(entries[0].at);
});

test('the log is capped so it cannot grow without bound', () => {
  const {context, store} = boot();
  for (let i = 0; i < 850; i += 1) context.window.gpEventLog('tick', `n${i}`);
  const entries = JSON.parse(store.get('gp-log'));
  assert.equal(entries.length, 800);
  assert.equal(entries.at(-1).message, 'n849');
});

test('a full storage sheds old entries instead of breaking the search', () => {
  const {context, store} = boot({failWrites: 1});
  assert.doesNotThrow(() => context.window.gpEventLog('tick', 'eins'));
  assert.ok(store.get('gp-log'), 'the retry must still persist something');
});

test('an unserialisable payload does not lose the entry', () => {
  const {context, store} = boot();
  const cyclic = {};
  cyclic.self = cyclic;
  context.window.gpEventLog('odd', 'zyklisch', cyclic);
  const entries = JSON.parse(store.get('gp-log'));
  assert.equal(entries.length, 1);
  assert.deepEqual(entries[0].data, {unserializable: true});
});

test('an existing writer is not displaced', () => {
  const existing = () => 'original';
  const {context} = boot({existing});
  assert.equal(context.window.gpEventLog, existing);
});
