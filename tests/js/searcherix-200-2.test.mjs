import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const pub = new URL('../../cloudflare/public/', import.meta.url);
const read = name => fs.readFileSync(new URL(name, pub), 'utf8');

test('the user-facing pages carry the Searcherix brand, not the technical product name', () => {
  const index = read('index.html');
  assert.ok(index.includes('<title>Searcherix</title>'));
  assert.ok(index.includes('<h1>Searcherix</h1>'));
  assert.ok(!index.includes('Plattformübergreifend'), 'das Eyebrow "Plattformübergreifend" entfällt');
  assert.ok(!index.includes('version-badge'), 'die Suche zeigt keine Version im Header');
  assert.ok(index.includes('<footer><span>Searcherix</span></footer>'));

  const favorites = read('favorites.html');
  assert.ok(favorites.includes('<title>Searcherix Favoriten</title>'));
  assert.ok(!favorites.includes('version-badge'));
  assert.ok(favorites.includes('<footer><span>Searcherix</span></footer>'));

  for (const name of ['controller-0450.js', 'favorites-150.js']) {
    const text = read(name);
    assert.ok(!text.includes('GenericParser'), `${name} soll keinen GenericParser-Text mehr in die Seite schreiben`);
    assert.ok(text.includes('Searcherix'), `${name} soll Searcherix schreiben`);
  }
});

test('the version and build identity stay visible under Log & Diagnose', () => {
  const eventlog = read('eventlog.html');
  assert.ok(eventlog.includes('version-badge'), 'das Log behält die Versionsanzeige');
  assert.ok(read('eventlog-0450.js').includes('GenericParser · Build'), 'das Log behält die technische Build-Identität im Footer');
  assert.match(read('ui-200.css'), /\[data-page="search"\] #worker-version\s*{[^}]*display:\s*none/,
    'der Versions-Chip an der Status-Karte der Suche ist ausgeblendet');
});

test('the PWA manifest and touch icons are wired for Searcherix', () => {
  const manifest = JSON.parse(read('manifest.webmanifest'));
  assert.equal(manifest.name, 'Searcherix');
  assert.equal(manifest.short_name, 'Searcherix');
  assert.deepEqual(manifest.icons.map(i => i.src), [
    './icons/searcherix-192.png',
    './icons/searcherix-512.png',
    './icons/searcherix-maskable-512.png'
  ]);

  const index = read('index.html');
  assert.ok(index.includes('rel="apple-touch-icon" href="./icons/searcherix-180.png"'));
  assert.ok(index.includes('apple-mobile-web-app-title" content="Searcherix"'));
  for (const icon of ['searcherix-180.png', 'searcherix-192.png', 'searcherix-512.png', 'searcherix-maskable-512.png']) {
    assert.ok(fs.existsSync(new URL(`icons/${icon}`, pub)), `${icon} liegt im icons-Ordner`);
    assert.ok(read('service-worker.js').includes(`"./icons/${icon}"`), `${icon} ist im Precache`);
  }
});
