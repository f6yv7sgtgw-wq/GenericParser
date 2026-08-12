import assert from 'node:assert/strict';
import test from 'node:test';

const {normalizeSize, sizeFrom, parseDetail, extractHtmlListings} =
  await import('../../pocs/vinted-browser/src/index.js');

test('a size label is accepted as a short token and read from structured objects', () => {
  assert.equal(normalizeSize('  M  '), 'M');
  assert.equal(normalizeSize({name: '38'}), '38');
  assert.equal(normalizeSize('Eine ganze Beschreibung der Passform'), null);
  assert.equal(normalizeSize('unbekannt'), null);
  assert.equal(normalizeSize(''), null);
});

test('labelled sizes are extracted in the spellings the marketplace uses', () => {
  assert.equal(sizeFrom('Zustand Sehr gut Größe M Marke King Louie'), 'M');
  assert.equal(sizeFrom('Grösse: 38'), '38');
  assert.equal(sizeFrom('Groesse 40 / L'), '40 / L');
  assert.equal(sizeFrom('Size XL'), 'XL');
});

test('prose after the label does not become a size', () => {
  // "ö" is not a word character, so a naive boundary would capture the "k".
  assert.equal(sizeFrom('Die Größe könnte etwas kleiner ausfallen'), null);
  assert.equal(sizeFrom('King Louie Kleid ohne Angabe'), null);
});

test('detail pages report the size as an enriched field', () => {
  const product = {
    '@type': 'Product',
    name: 'King Louie Kleid',
    size: 'M',
    itemCondition: 'Sehr gut',
    description: 'Schönes Kleid',
    image: 'https://www.vinted.de/bild.jpg',
    offers: {price: '39.90'}
  };
  const html = `<html><head><script type="application/ld+json">${JSON.stringify(product)}<\/script></head><body>Größe M</body></html>`;
  const listing = {id: 'vinted:1', title: 'x', url: 'https://www.vinted.de/items/1', condition: null, size: null, price: null, detail_status: 'pending', detail_fields: []};
  const result = parseDetail(html, listing);
  assert.equal(result.size, 'M');
  assert.ok(result.detail_fields.includes('size'));
  assert.equal(result.detail_status, 'ok');
});

test('a detail page without a size leaves the field null instead of guessing', () => {
  const html = '<html><body>King Louie Kleid 39,90 € Sehr gut</body></html>';
  const listing = {id: 'vinted:2', title: 'x', url: 'https://www.vinted.de/items/2', condition: null, size: null, price: null, detail_status: 'pending', detail_fields: []};
  const result = parseDetail(html, listing);
  assert.equal(result.size, null);
  assert.ok(!result.detail_fields.includes('size'));
});

test('catalog cards already carry the size so the facet is not limited to enriched rows', () => {
  const catalog = '<a href="/items/123-king-louie-kleid">King Louie</a><span>Größe M</span><span>39,90 €</span>';
  const [item] = extractHtmlListings(catalog);
  assert.equal(item.id, 'vinted:123');
  assert.equal(item.size, 'M');
});

test('catalog cards carry their photo so the grid is not empty until enrichment', async () => {
  const {imageFrom, extractHtmlListings} = await import('../../pocs/vinted-browser/src/index.js');
  const card = '<div><img src="https://images1.vinted.net/tc/03_abc/1234.jpeg?s=xyz" alt="King Louie">'
    + '<a href="/items/321-king-louie-kleid">King Louie</a><span>39,90 €</span></div>';
  const [item] = extractHtmlListings(card);
  assert.equal(item.image_url, 'https://images1.vinted.net/tc/03_abc/1234.jpeg?s=xyz');
  // Avatars, icons and tracking pixels from other hosts must not become a photo.
  assert.equal(imageFrom('<img src="https://cdn.example.com/avatar.png">'), null);
  assert.equal(imageFrom('<img src="/assets/logo.svg">'), null);
  assert.equal(imageFrom('<img data-src="https://images1.vinted.net/tc/9/9.webp">'),
    'https://images1.vinted.net/tc/9/9.webp');
});
