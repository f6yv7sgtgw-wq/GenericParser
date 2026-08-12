import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../../cloudflare/public/ui-180.js', import.meta.url), 'utf8');

function element(tag = 'div') {
  const node = {
    tagName: tag.toUpperCase(),
    children: [],
    dataset: {},
    attributes: {},
    classList: {
      _set: new Set(),
      add(...names) { names.forEach(n => this._set.add(n)); },
      contains(name) { return this._set.has(name); }
    },
    listeners: {},
    textContent: '',
    innerHTML: '',
    value: '',
    type: '',
    options: [],
    append(...nodes) { this.children.push(...nodes); },
    closest() { return null; },
    addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
    dispatchEvent(event) { (this.listeners[event.type] || []).forEach(h => h(event)); return true; },
    setAttribute(name, value) { this.attributes[name] = String(value); },
    getAttribute(name) { return this.attributes[name] ?? null; },
    querySelector() { return null; }
  };
  return node;
}

function boot({withSelect = true} = {}) {
  const nodes = new Map();
  const results = element('section');
  Object.defineProperty(results, 'children', {
    get() { return this._kids ||= []; },
    set(value) { this._kids = value; }
  });
  nodes.set('results', results);

  const field = element('label');
  if (withSelect) {
    const select = element('select');
    select.options = [
      {value: 'auto', textContent: 'Alle Plattformen'},
      {value: 'vinted', textContent: 'Vinted'}
    ];
    select.value = 'auto';
    select.closest = () => field;
    nodes.set('search-source', select);
  }

  const windowListeners = {};
  const context = {
    console, Map, Set, Array, String, Boolean, Object, Event,
    document: {
      readyState: 'complete',
      getElementById: id => nodes.get(id) || null,
      createElement: tag => element(tag),
      addEventListener() {}
    },
    window: {
      addEventListener(type, handler) { (windowListeners[type] ||= []).push(handler); }
    }
  };
  context.globalThis = context;
  vm.runInNewContext(source, context, {filename: 'ui-180.js'});
  return {context, nodes, field, windowListeners};
}

test('the platform select stays the data source behind the segment buttons', () => {
  const {nodes, field} = boot();
  const select = nodes.get('search-source');
  const group = field.children[0];
  assert.ok(group, 'segment group was not attached');
  assert.equal(group.children.length, 2);
  assert.equal(group.children[0].getAttribute('aria-pressed'), 'true');

  group.children[1].dispatchEvent({type: 'click'});
  assert.equal(select.value, 'vinted', 'clicking a segment must write through to the select');
  assert.equal(group.children[1].getAttribute('aria-pressed'), 'true');
  assert.equal(group.children[0].getAttribute('aria-pressed'), 'false');
});

test('a missing select leaves the search bar untouched instead of throwing', () => {
  const {field} = boot({withSelect: false});
  assert.equal(field.children.length, 0);
});

test('placeholders appear only while the result list is still empty', () => {
  const {context, nodes, windowListeners} = boot();
  const results = nodes.get('results');
  const [onRunState] = windowListeners['gp-search-run-state'];

  onRunState({detail: {running: true}});
  assert.match(results.innerHTML, /skeleton-grid/);
  assert.equal((results.innerHTML.match(/skeleton-card/g) || []).length, 6);

  // Sobald echte Treffer im Baum stehen, darf ein weiterer Lauf sie nicht
  // hinter Platzhaltern verstecken.
  results.innerHTML = '<article>Treffer</article>';
  results.children = [element('article')];
  onRunState({detail: {running: true}});
  assert.equal(results.innerHTML, '<article>Treffer</article>');

  assert.equal(typeof context.window.GPUI180.skeletonMarkup, 'function');
});

test('placeholders are cleared when the run ends without results', () => {
  const {nodes, windowListeners} = boot();
  const results = nodes.get('results');
  const [onRunState] = windowListeners['gp-search-run-state'];
  onRunState({detail: {running: true}});
  results.querySelector = selector => (selector === '.skeleton-grid' ? element('div') : null);
  onRunState({detail: {running: false}});
  assert.equal(results.innerHTML, '');
});
