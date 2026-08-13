import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const pub = new URL('../../cloudflare/public/', import.meta.url);
const read = name => fs.readFileSync(new URL(name, pub), 'utf8');

const source = read('ui-160.js');
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

test('criterion labels keep their nouns capitalised in the search summary', () => {
  assert.equal(context.window.GPUI160.criterionCase('Letzte 90 Tage'), 'letzte 90 Tage');
  assert.equal(context.window.GPUI160.criterionCase('Letztes Jahr'), 'letztes Jahr');
  assert.equal(context.window.GPUI160.criterionCase(''), '');
  assert.equal(context.window.GPUI160.criterionCase(undefined), '');
});

test('the footer identity dropped the historical Mobile branding everywhere', () => {
  for (const name of ['controller-0450.js', 'favorites-150.js', 'eventlog-0450.js']) {
    const text = read(name);
    assert.ok(text.includes('GenericParser · Build'), `${name} soll "GenericParser · Build" schreiben`);
    assert.ok(!text.includes('GenericParser Mobile'), `${name} soll kein "GenericParser Mobile" mehr tragen`);
  }
  const manifest = JSON.parse(read('manifest.webmanifest'));
  assert.equal(manifest.name, 'GenericParser');
  assert.equal(manifest.short_name, 'GenericParser');
});

test('the 2.0 polish stylesheet is linked and precached', () => {
  assert.ok(read('index.html').includes('ui-200.css'));
  assert.ok(read('favorites.html').includes('ui-200.css'));
  assert.ok(read('service-worker.js').includes('"./ui-200.css"'));
});

test('the polish stylesheet pins the card footer and stretches grid rows', () => {
  const css = read('ui-200.css');
  assert.match(css, /\.results\s*{[^}]*align-items:\s*stretch/);
  assert.match(css, /\.listing-footer\s*{[^}]*margin-top:\s*auto/);
  assert.match(css, /\.filter-reset\s*{[^}]*white-space:\s*nowrap/);
});
