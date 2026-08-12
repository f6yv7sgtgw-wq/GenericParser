import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const app = fs.readFileSync(new URL('../../cloudflare/public/app.js', import.meta.url), 'utf8');
const line = (prefix) => app.split('\n').find(value => value.startsWith(prefix));

function evaluate(identity) {
  const context = {window: {GP_BUILD_IDENTITY: identity}, Math};
  const source = [
    line('function protectionDelaysOn'),
    line('function rotatesSources'),
    line('function adaptiveDelay')
  ].join('\n');
  vm.runInNewContext(`${source}\nthis.api = {protectionDelaysOn, rotatesSources, adaptiveDelay};`, context);
  return context.api;
}

test('the paid profile throttles nothing, whatever the packet latency was', () => {
  const api = evaluate({workerPlan: 'paid', protectionDelays: false});
  assert.equal(api.protectionDelaysOn(), false);
  for (const latency of [0, 900, 1500, 3000, 9000]) {
    assert.equal(api.adaptiveDelay(0, latency), 0, `latency ${latency}`);
  }
});

test('an explicit protectionDelays flag is enough on its own', () => {
  assert.equal(evaluate({workerPlan: 'free', protectionDelays: false}).protectionDelaysOn(), false);
  assert.equal(evaluate({workerPlan: 'paid'}).protectionDelaysOn(), false);
});

test('a free profile keeps the latency ladder', () => {
  const api = evaluate({workerPlan: 'free', protectionDelays: true});
  assert.equal(api.protectionDelaysOn(), true);
  assert.equal(api.adaptiveDelay(0, 500), 300);
  assert.equal(api.adaptiveDelay(0, 1500), 800);
  assert.equal(api.adaptiveDelay(0, 3000), 2000);
  // Genau dieser Wert war der Fünf-Sekunden-Timer.
  assert.equal(api.adaptiveDelay(0, 9000), 5000);
});

test('a missing identity stays cautious and keeps throttling', () => {
  assert.equal(evaluate(undefined).protectionDelaysOn(), true);
});

test('a rotating search is not paused between packets', () => {
  const api = evaluate({workerPlan: 'free', protectionDelays: true});
  // Bis eine Quelle wieder an der Reihe ist, wurden die anderen bedient; eine
  // zusätzliche Pause würde die langsamste Quelle alle übrigen ausbremsen.
  assert.equal(api.rotatesSources({base: {source: 'auto'}}), true);
  assert.equal(api.rotatesSources({base: {}}), true);
  assert.equal(api.rotatesSources({base: {source: 'vinted'}}), false);
  assert.equal(api.rotatesSources({base: {source: 'kleinanzeigen'}}), false);
});

test('the countdown is skipped for rotating searches and for a zero delay', () => {
  const call = app.split('\n').find(value => value.includes('await countdown(s.nextDelay'));
  assert.ok(call, 'countdown call missing');
  assert.match(call, /s\.nextDelay>0/);
  assert.match(call, /!rotatesSources\(s\)/);
});
