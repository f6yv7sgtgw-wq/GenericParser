import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../../cloudflare/public/ui-160.js', import.meta.url), 'utf8');
const context = {
  console,
  document: {readyState: 'loading', addEventListener() {}},
  window: {addEventListener() {}},
  localStorage: {getItem() { return null; }, setItem() {}},
  Event,
  Map,
  Set
};
vm.runInNewContext(source, context, {filename: 'ui-160.js'});

test('comma terms preserve umlauts and slash variants while removing duplicates', () => {
  const actual = Array.from(context.window.GPUI160.parseTermList('Märklin, H0/AC, märklin, ÖVP, '));
  assert.deepEqual(actual, ['Märklin', 'H0/AC', 'ÖVP']);
});

test('array terms are trimmed and empty entries are ignored', () => {
  const actual = Array.from(context.window.GPUI160.parseTermList(['  PAL  ', '', 'NTSC', 'pal']));
  assert.deepEqual(actual, ['PAL', 'NTSC']);
});
