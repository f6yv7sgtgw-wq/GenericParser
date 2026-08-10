(async () => {
  'use strict';

  const identity = await window.GP_BUILD_IDENTITY_READY;
  const store = window.GPFavorites;
  if (!identity || !store) throw new Error('Favoritenmodul konnte nicht geladen werden');

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const money = value => Number(value).toLocaleString('de-DE', {minimumFractionDigits: 0, maximumFractionDigits: 2});
  const sourceLabel = source => source === 'ebay' ? 'eBay' : source === 'vinted' ? 'Vinted' : source === 'kleinanzeigen' ? 'Kleinanzeigen' : 'Quelle';

  document.title = `GenericParser Favoriten ${identity.version}`;
  document.querySelectorAll('[data-version]').forEach(node => { node.textContent = identity.version; });
  const footer = document.querySelector('footer span');
  if (footer) footer.textContent = `GenericParser Mobile · Build ${identity.buildId}`;

  function formatPrice(row) {
    if (row.total_price != null) return `${money(row.total_price)} € gesamt`;
    if (row.source === 'ebay' && row.item_price != null) return `${money(row.item_price)} € + Versand offen`;
    if (row.price != null) return `${money(row.price)} €`;
    return row.price_raw || 'Preis offen';
  }

  function shipping(row) {
    if (row.shipping_available === false) return 'Nur Abholung';
    if (row.shipping_cost != null) return Number(row.shipping_cost) === 0 ? 'Versand kostenlos' : `Versand ${money(row.shipping_cost)} €`;
    if (row.shipping_available === true) return 'Versandkosten offen';
    return '';
  }

  function card(row) {
    const meta = [shipping(row), row.saved_at ? `Gespeichert ${new Date(row.saved_at).toLocaleString('de-DE')}` : ''].filter(Boolean);
    const color = ['green','yellow','orange','red'].includes(row.traffic_color) ? row.traffic_color : 'yellow';
    const trafficLabel = row.traffic_label || (color === 'green' ? 'Passender Treffer' : color === 'red' ? 'Unpassend' : 'Prüfen');
    return `<article class="listing favorite-card traffic-${esc(color)} source-${esc(row.source)}" data-favorite-key="${esc(row.favorite_key)}"><button class="favorite-toggle is-favorite" type="button" data-favorite-key="${esc(row.favorite_key)}" aria-label="Aus Favoriten entfernen" aria-pressed="true">★</button><div class="listing-image">${row.image_url ? `<img src="${esc(row.image_url)}" loading="lazy" alt="">` : 'KEIN BILD'}</div><div class="listing-body"><div class="listing-topline"><div><div class="listing-badges"><span class="traffic-pill traffic-${esc(color)}"><span class="traffic-dot"></span>${esc(trafficLabel)}</span><span class="source-badge">${esc(sourceLabel(row.source))}</span><span class="product-class-badge">${esc(row.product_class_label || 'Produktart offen')}</span>${row.condition ? `<span>${esc(row.condition)}</span>` : ''}${row.scope ? `<span>${esc(row.scope)}</span>` : ''}${row.listing_format ? `<span>${esc(row.listing_format)}</span>` : ''}</div><h3><a href="${esc(row.url)}" target="_blank" rel="noopener">${esc(row.title)}</a></h3></div><strong class="price">${esc(formatPrice(row))}</strong></div>${row.reason ? `<p class="reason">${esc(row.reason)}</p>` : ''}<div class="listing-footer"><div class="meta">${meta.map(value => `<span>${esc(value)}</span>`).join('')}</div><a class="listing-link" href="${esc(row.url)}" target="_blank" rel="noopener">Anzeige öffnen</a></div></div></article>`;
  }

  function render() {
    const rows = store.all();
    const source = document.getElementById('favorite-source').value;
    const visible = source === 'all' ? rows : rows.filter(row => row.source === source);
    document.getElementById('favorite-total').textContent = source === 'all' ? String(rows.length) : `${visible.length} / ${rows.length}`;
    document.getElementById('favorites-results').innerHTML = visible.length
      ? visible.map(card).join('')
      : '<div class="favorites-empty">Noch keine passenden Favoriten gespeichert. In der Suche markierst du ein Angebot über den Stern oben rechts.</div>';
    document.getElementById('clear-favorites').disabled = rows.length === 0;
  }

  document.getElementById('favorite-source').addEventListener('change', render);
  document.getElementById('favorites-results').addEventListener('click', event => {
    const button = event.target.closest?.('.favorite-toggle');
    if (!button) return;
    store.remove(button.dataset.favoriteKey || '');
  });
  document.getElementById('clear-favorites').addEventListener('click', () => {
    if (store.all().length && window.confirm('Alle gespeicherten Favoriten aus diesem Browser entfernen?')) store.clear();
  });
  window.addEventListener('gp-favorites-changed', render);
  render();
})().catch(error => {
  const container = document.getElementById('favorites-results');
  if (container) {
    container.replaceChildren();
    const message = document.createElement('div');
    message.className = 'favorites-empty';
    message.textContent = `Favoriten konnten nicht geladen werden: ${String(error?.message || error)}`;
    container.append(message);
  }
});
