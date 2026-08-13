import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// 1.9.3: Der Quellen-Status benennt den Lebenszyklus ehrlich — "Erfolgreich"
// nach jedem Zwischenpaket war verwirrend, solange weiter Treffer kamen.

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
const label = context.window.GPUI160.sourceStatusLabel;

test('a source without any packet has not started yet', () => {
  assert.equal(label({status: 'idle'}), 'Noch nicht gestartet');
  assert.equal(label({status: 'disabled'}), 'Nicht ausgewählt');
});

test('a source that delivered packets but has not finished is working', () => {
  assert.equal(label({status: 'ok', ended: false}), 'Arbeitet');
});

test('a finished source is completed, not merely successful', () => {
  assert.equal(label({status: 'ok', ended: true}), 'Abgeschlossen');
  assert.equal(label({status: 'empty', ended: true}), 'Abgeschlossen · keine Treffer');
});

test('warnings and errors are stated, including the retry attempt', () => {
  assert.equal(label({status: 'blocked', retry: {attempt: 1, limit: 2}}), 'Blockiert · neuer Anlauf 1/2');
  assert.equal(label({status: 'blocked', ended: true}), 'Blockiert');
  assert.equal(label({status: 'rate_limited', ended: true}), 'Gedrosselt');
});

test('an interrupted run leaves the source stopped, not completed', () => {
  assert.equal(label({status: 'stopped'}), 'Angehalten');
});
