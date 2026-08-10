(() => {
  'use strict';

  const STORAGE_KEY = 'generic-parser-favorites-v1';
  const MAX_FAVORITES = 500;
  const text = (value, max = 500) => String(value ?? '').trim().slice(0, max);
  const number = value => value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);

  function sourceOf(listing) {
    const raw = text(listing?.source || listing?.source_label).toLowerCase();
    const id = text(listing?.id).toLowerCase();
    if (raw.includes('vinted') || id.startsWith('vinted:')) return 'vinted';
    if (raw.includes('ebay') || id.startsWith('ebay:')) return 'ebay';
    if (raw.includes('kleinanzeigen')) return 'kleinanzeigen';
    try {
      const host = new URL(listing?.url || '', location.href).hostname.toLowerCase();
      if (host.includes('vinted.')) return 'vinted';
      if (host.includes('ebay.')) return 'ebay';
      if (host.includes('kleinanzeigen.')) return 'kleinanzeigen';
    } catch {}
    return 'unknown';
  }

  function keyOf(listing) {
    const source = sourceOf(listing);
    const identity = text(listing?.id || listing?.url, 1000);
    return identity ? `${source}:${identity}` : '';
  }

  function read() {
    try {
      const rows = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      return Array.isArray(rows) ? rows.filter(row => row && row.favorite_key && row.url) : [];
    } catch {
      return [];
    }
  }

  function write(rows) {
    const unique = new Map();
    for (const row of rows) {
      if (row?.favorite_key) unique.set(row.favorite_key, row);
    }
    const saved = [...unique.values()]
      .sort((a, b) => String(b.saved_at || '').localeCompare(String(a.saved_at || '')))
      .slice(0, MAX_FAVORITES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
    updateCounts(saved.length);
    window.dispatchEvent(new CustomEvent('gp-favorites-changed', {detail: {count: saved.length}}));
    return saved;
  }

  function safeUrl(value) {
    try {
      const url = new URL(value, location.href);
      return url.protocol === 'https:' ? url.toString() : '';
    } catch {
      return '';
    }
  }

  function snapshot(listing) {
    const source = sourceOf(listing);
    const favoriteKey = keyOf(listing);
    const info = listing?.result_info && typeof listing.result_info === 'object' ? listing.result_info : {};
    const classification = listing?.product_classification && typeof listing.product_classification === 'object' ? listing.product_classification : {};
    const traffic = listing?.traffic_light && typeof listing.traffic_light === 'object' ? listing.traffic_light : {};
    const match = listing?.match && typeof listing.match === 'object' ? listing.match : {};
    return {
      favorite_key: favoriteKey,
      id: text(listing?.id, 300),
      title: text(listing?.title, 500),
      url: safeUrl(listing?.url),
      image_url: safeUrl(listing?.image_url),
      source,
      source_label: source === 'ebay' ? 'eBay' : source === 'vinted' ? 'Vinted' : source === 'kleinanzeigen' ? 'Kleinanzeigen' : 'Quelle',
      item_price: number(listing?.item_price),
      shipping_cost: number(listing?.shipping_cost),
      total_price: number(listing?.total_price),
      price: number(listing?.price),
      price_raw: text(listing?.price_raw, 120),
      currency: text(listing?.currency || 'EUR', 10),
      shipping_available: listing?.shipping_available === true ? true : listing?.shipping_available === false ? false : null,
      listing_format: text(info.listing_format || listing?.listing_format, 100),
      auction: Boolean(listing?.auction),
      condition: text(info.condition || listing?.condition, 100),
      scope: text(info.scope, 100),
      product_class: text(classification.code || info.product_class || 'unknown', 80),
      product_class_label: text(classification.label || info.product_class_label || 'Produktart offen', 120),
      traffic_color: text(traffic.color || (match.decision === 'reject' ? 'red' : match.decision === 'accept' ? 'green' : 'yellow'), 20),
      traffic_label: text(traffic.label || '', 100),
      reason: text(match.reason || traffic.reason, 300),
      saved_at: new Date().toISOString(),
      storage_scope: 'browser-local-user-selected',
      contains_seller_data: false
    };
  }

  function all() {
    return read().sort((a, b) => String(b.saved_at || '').localeCompare(String(a.saved_at || '')));
  }

  function has(listingOrKey) {
    const key = typeof listingOrKey === 'string' ? listingOrKey : keyOf(listingOrKey);
    return Boolean(key && read().some(row => row.favorite_key === key));
  }

  function add(listing) {
    const row = snapshot(listing);
    if (!row.favorite_key || !row.title || !row.url) return false;
    const rows = read().filter(item => item.favorite_key !== row.favorite_key);
    write([row, ...rows]);
    return true;
  }

  function remove(listingOrKey) {
    const key = typeof listingOrKey === 'string' ? listingOrKey : keyOf(listingOrKey);
    if (!key) return false;
    const rows = read();
    const next = rows.filter(row => row.favorite_key !== key);
    if (next.length === rows.length) return false;
    write(next);
    return true;
  }

  function toggle(listing) {
    if (has(listing)) {
      remove(listing);
      return false;
    }
    return add(listing);
  }

  function clear() {
    write([]);
  }

  function updateCounts(count = read().length) {
    document.querySelectorAll('[data-favorite-count]').forEach(node => {
      node.textContent = String(count);
    });
  }

  window.GPFavorites = {STORAGE_KEY, all, has, add, remove, toggle, clear, keyOf, sourceOf, snapshot, updateCounts};
  updateCounts();
  window.addEventListener('storage', event => {
    if (event.key === STORAGE_KEY) updateCounts();
  });
})();
