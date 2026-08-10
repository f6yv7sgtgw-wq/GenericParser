import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../../cloudflare/public/favorites-store-150.js', import.meta.url), 'utf8');

function loadStore(initial = null) {
  const values = new Map();
  if (initial !== null) values.set('generic-parser-favorites-v1', initial);
  const events = [];
  const counters = [{textContent: ''}, {textContent: ''}];
  const localStorage = {
    getItem: key => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: key => values.delete(key)
  };
  class CustomEvent {
    constructor(type, options = {}) {
      this.type = type;
      this.detail = options.detail;
    }
  }
  const window = {
    addEventListener() {},
    dispatchEvent: event => events.push(event)
  };
  const context = {
    CustomEvent,
    URL,
    document: {querySelectorAll: () => counters},
    localStorage,
    location: {href: 'https://genericparser.example/'},
    window
  };
  vm.runInNewContext(source, context, {filename: 'favorites-store-150.js'});
  return {store: window.GPFavorites, values, events, counters};
}

test('favorite snapshot stores only the deliberate bounded field set', () => {
  const {store, values, events, counters} = loadStore();
  const listing = {
    id: 'ebay:123',
    source: 'ebay',
    title: 'Super Mario Kart 8 Deluxe',
    url: 'https://www.ebay.de/itm/123',
    image_url: 'https://i.ebayimg.com/images/123.jpg',
    description: 'must not be persisted',
    seller: {username: 'must-not-survive', feedbackScore: 999},
    seller_id: 'secret-seller-id',
    item_price: 30,
    shipping_cost: 4.5,
    total_price: 34.5,
    price: 34.5,
    product_classification: {code: 'main_product', label: 'Hauptprodukt'},
    result_info: {condition: 'gebraucht', scope: 'Einzelangebot'},
    traffic_light: {color: 'green', label: 'Passender Treffer'},
    match: {reason: 'Titel und Produktart passen'}
  };

  assert.equal(store.add(listing), true);
  assert.equal(store.has(listing), true);
  const [saved] = JSON.parse(values.get(store.STORAGE_KEY));
  assert.equal(saved.title, listing.title);
  assert.equal(saved.total_price, 34.5);
  assert.equal(saved.contains_seller_data, false);
  assert.equal('description' in saved, false);
  assert.equal('seller' in saved, false);
  assert.equal('seller_id' in saved, false);
  assert.equal(JSON.stringify(saved).includes('must-not-survive'), false);
  assert.equal(events.at(-1).detail.count, 1);
  assert.deepEqual(counters.map(node => node.textContent), ['1', '1']);

  assert.equal(store.toggle(listing), false);
  assert.equal(store.all().length, 0);
});

test('unsafe URLs and malformed storage cannot create a favorite', () => {
  const {store} = loadStore('{not-json');
  assert.deepEqual(Array.from(store.all()), []);
  assert.equal(store.add({id: 'ebay:bad', source: 'ebay', title: 'Bad', url: 'javascript:alert(1)'}), false);
  assert.equal(store.all().length, 0);
});
