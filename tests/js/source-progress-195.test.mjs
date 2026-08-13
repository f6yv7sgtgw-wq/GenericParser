import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// 1.9.5: Die anonyme Blättertiefe ist ein reguläres Ende und wird so benannt.

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

test('the anonymous depth end reads as completed, not as an error', () => {
  assert.equal(
    label({status: 'empty', ended: true, reason: 'vinted_anonymous_depth_reached'}),
    'Abgeschlossen · anonyme Blättertiefe erreicht'
  );
});

test('an ordinary empty end keeps its plain label', () => {
  assert.equal(label({status: 'empty', ended: true, reason: ''}), 'Abgeschlossen · keine Treffer');
});
