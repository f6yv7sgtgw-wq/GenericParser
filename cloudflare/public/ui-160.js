(() => {
  'use strict';

  const RECENT_KEY = 'generic-parser-recent-searches-v1';
  const PROFILE_PREFIX = 'gp-profile:';
  const TERM_FIELDS = ['required-terms', 'excluded-terms', 'model-patterns', 'brands'];
  const SOURCE_LABELS = {auto: 'Alle Plattformen', kleinanzeigen: 'Kleinanzeigen', vinted: 'Vinted', ebay: 'eBay'};
  const FILTERS = [
    {id: 'sort-by', defaultValue: 'relevance', label: 'Sortierung'},
    {id: 'filter-traffic', defaultValue: 'without-red', label: 'Status'},
    {id: 'filter-source', defaultValue: 'all', label: 'Plattform'},
    {id: 'filter-product-class', defaultValue: 'all', label: 'Produktart'},
    {id: 'filter-condition', defaultValue: 'all', label: 'Zustand'},
    {id: 'filter-price-min', defaultValue: '', label: 'Preis ab', suffix: ' €'},
    {id: 'filter-price-max', defaultValue: '', label: 'Preis bis', suffix: ' €'},
    {id: 'filter-shipping', defaultValue: 'all', label: 'Versand'},
    {id: 'filter-scope', defaultValue: 'all', label: 'Umfang'},
    {id: 'filter-format', defaultValue: 'no-auction', label: 'Angebotsart'},
    {id: 'filter-known-total', defaultValue: 'all', label: 'Gesamtpreis'},
    {id: 'filter-favorites', defaultValue: 'all', label: 'Favoriten'},
    {id: 'filter-size', defaultValue: 'all', label: 'Größe'}
  ];
  const sourceState = new Map();
  const editors = new Map();

  function parseTermList(value) {
    const parts = Array.isArray(value) ? value : String(value ?? '').split(/[\n,]+/);
    const result = [];
    const seen = new Set();
    for (const part of parts) {
      const text = String(part).trim();
      const key = text.toLocaleLowerCase('de-DE');
      if (!text || seen.has(key)) continue;
      seen.add(key);
      result.push(text);
    }
    return result;
  }

  function writeTerms(hidden, terms) {
    hidden.value = parseTermList(terms).join(', ');
    hidden.dispatchEvent(new Event('input', {bubbles: true}));
    hidden.dispatchEvent(new Event('change', {bubbles: true}));
  }

  function createChip(text, remove) {
    const chip = document.createElement('span');
    chip.className = 'term-chip';
    chip.append(document.createTextNode(text));
    const button = document.createElement('button');
    button.type = 'button';
    button.setAttribute('aria-label', `„${text}“ entfernen`);
    button.textContent = '×';
    button.addEventListener('click', remove);
    chip.append(button);
    return chip;
  }

  function enhanceTermField(id) {
    const hidden = document.getElementById(id);
    const entry = document.querySelector(`[data-term-entry="${id}"]`);
    const chipHost = document.querySelector(`[data-term-chips="${id}"]`);
    if (!hidden || !entry || !chipHost) return null;
    let terms = [];

    const render = () => {
      terms = parseTermList(hidden.value);
      chipHost.replaceChildren(...terms.map(term => createChip(term, () => {
        terms = terms.filter(item => item !== term);
        writeTerms(hidden, terms);
        render();
        updateCriteriaCount();
        updateSearchSummary();
        entry.focus();
      })));
    };
    const add = raw => {
      const additions = parseTermList(raw);
      if (!additions.length) return;
      terms = parseTermList([...terms, ...additions]);
      writeTerms(hidden, terms);
      entry.value = '';
      render();
      updateCriteriaCount();
      updateSearchSummary();
    };
    const sync = () => {
      terms = parseTermList(hidden.value);
      writeTerms(hidden, terms);
      render();
      updateCriteriaCount();
      updateSearchSummary();
    };

    entry.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ',') {
        event.preventDefault();
        add(entry.value);
      } else if (event.key === 'Backspace' && !entry.value && terms.length) {
        terms.pop();
        writeTerms(hidden, terms);
        render();
        updateCriteriaCount();
        updateSearchSummary();
      }
    });
    entry.addEventListener('paste', event => {
      const value = event.clipboardData?.getData('text') || '';
      if (!/[\n,]/.test(value)) return;
      event.preventDefault();
      add(value);
    });
    entry.addEventListener('blur', () => add(entry.value));
    hidden.addEventListener('gp-chip-sync', sync);
    render();
    const editor = {add, sync, values: () => [...terms]};
    editors.set(id, editor);
    return editor;
  }

  function syncEditors() {
    for (const editor of editors.values()) editor.sync();
  }

  function selectedText(element) {
    if (!element) return '';
    if (element.tagName === 'SELECT') return element.selectedOptions[0]?.textContent?.trim() || element.value;
    return element.value.trim();
  }

  function updateCriteriaCount() {
    const count = TERM_FIELDS.reduce((sum, id) => sum + parseTermList(document.getElementById(id)?.value).length, 0)
      + ['max-price', 'postal-code', 'location-id', 'radius-km', 'max-results'].filter(id => document.getElementById(id)?.value?.trim()).length
      + ['accept-bundles', 'accept-incomplete'].filter(id => document.getElementById(id)?.checked).length
      // Auctions are searched by default; only switching them off is a deviation.
      + (document.getElementById('include-ebay-auctions')?.checked === false ? 1 : 0);
    const badge = document.getElementById('criteria-count');
    if (badge) badge.textContent = count ? `${count} aktiv` : 'optional';
  }

  function updateSearchSummary() {
    const query = document.getElementById('query')?.value.trim();
    const source = document.getElementById('search-source')?.value || 'auto';
    const required = parseTermList(document.getElementById('required-terms')?.value).length;
    const excluded = parseTermList(document.getElementById('excluded-terms')?.value).length;
    const maxPrice = document.getElementById('max-price')?.value.trim();
    const count = document.getElementById('results-count')?.textContent?.trim();
    const parts = [];
    if (query) parts.push(`„${query}“`);
    parts.push(SOURCE_LABELS[source] || source);
    if (required) parts.push(`${required} Pflichtbegriff${required === 1 ? '' : 'e'}`);
    if (excluded) parts.push(`${excluded} Ausschlussbegriff${excluded === 1 ? '' : 'e'}`);
    if (maxPrice) parts.push(`bis ${maxPrice} €`);
    if (count && count !== '0') parts.push(`${count} sichtbar`);
    const target = document.getElementById('search-summary');
    if (target) target.textContent = query ? parts.join(' · ') : 'Suchbegriff eingeben und eine oder alle Plattformen auswählen.';
  }

  function readRecent() {
    try {
      const parsed = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
      return Array.isArray(parsed) ? parsed.filter(item => item && item.query).slice(0, 6) : [];
    } catch {
      return [];
    }
  }

  function searchSnapshot() {
    return {
      query: document.getElementById('query')?.value.trim() || '',
      source: document.getElementById('search-source')?.value || 'auto',
      required: document.getElementById('required-terms')?.value || '',
      excluded: document.getElementById('excluded-terms')?.value || '',
      models: document.getElementById('model-patterns')?.value || '',
      brands: document.getElementById('brands')?.value || '',
      maxPrice: document.getElementById('max-price')?.value || '',
      savedAt: Date.now()
    };
  }

  function saveRecent() {
    const item = searchSnapshot();
    if (!item.query) return;
    const signature = `${item.query.toLocaleLowerCase('de-DE')}|${item.source}|${item.required}|${item.excluded}`;
    const next = [item, ...readRecent().filter(entry => `${entry.query.toLocaleLowerCase('de-DE')}|${entry.source}|${entry.required}|${entry.excluded}` !== signature)].slice(0, 6);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
    renderRecent();
  }

  function loadSnapshot(item) {
    const values = {
      query: item.query,
      'search-source': item.source || 'auto',
      'required-terms': item.required || '',
      'excluded-terms': item.excluded || '',
      'model-patterns': item.models || '',
      brands: item.brands || '',
      'max-price': item.maxPrice || ''
    };
    for (const [id, value] of Object.entries(values)) {
      const element = document.getElementById(id);
      if (element) element.value = value;
    }
    syncEditors();
    updateCriteriaCount();
    updateSearchSummary();
    document.getElementById('query')?.focus();
  }

  function renderRecent() {
    const host = document.getElementById('recent-searches');
    if (!host) return;
    const recent = readRecent();
    host.replaceChildren();
    host.classList.toggle('hidden', !recent.length);
    if (!recent.length) return;
    const label = document.createElement('span');
    label.textContent = 'Letzte Suchen:';
    host.append(label);
    for (const item of recent) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'recent-search';
      button.textContent = `${item.query} · ${SOURCE_LABELS[item.source] || item.source}`;
      button.addEventListener('click', () => loadSnapshot(item));
      host.append(button);
    }
  }

  function profileKeys() {
    return Object.keys(localStorage).filter(key => key.startsWith(PROFILE_PREFIX)).sort((a, b) => a.localeCompare(b, 'de'));
  }

  function rebuildProfiles(selected = '') {
    const select = document.getElementById('profiles');
    if (!select) return;
    select.innerHTML = '<option value="">– auswählen –</option>';
    for (const key of profileKeys()) {
      const option = document.createElement('option');
      option.value = key;
      option.textContent = key.slice(PROFILE_PREFIX.length);
      select.append(option);
    }
    select.value = profileKeys().includes(selected) ? selected : '';
  }

  function updateProfilePreview() {
    const select = document.getElementById('profiles');
    const preview = document.getElementById('profile-preview');
    if (!select || !preview || !select.value) {
      if (preview) preview.textContent = 'Kein Profil ausgewählt.';
      return;
    }
    try {
      const data = JSON.parse(localStorage.getItem(select.value) || '{}');
      const parts = [data.query || 'Ohne Suchbegriff', SOURCE_LABELS[data['search-source']] || 'Alle Plattformen'];
      const required = parseTermList(data['required-terms']).length;
      const excluded = parseTermList(data['excluded-terms']).length;
      if (required) parts.push(`${required} Pflichtbegriffe`);
      if (excluded) parts.push(`${excluded} Ausschlussbegriffe`);
      if (data['max-price']) parts.push(`bis ${data['max-price']} €`);
      preview.textContent = parts.join(' · ');
    } catch {
      preview.textContent = 'Profil konnte nicht gelesen werden.';
    }
  }

  function renameProfile() {
    const select = document.getElementById('profiles');
    if (!select?.value) return;
    const currentName = select.value.slice(PROFILE_PREFIX.length);
    const nextName = window.prompt('Neuer Profilname', currentName)?.trim();
    if (!nextName || nextName === currentName) return;
    const nextKey = PROFILE_PREFIX + nextName;
    localStorage.setItem(nextKey, localStorage.getItem(select.value) || '{}');
    localStorage.removeItem(select.value);
    document.getElementById('profile-name').value = nextName;
    rebuildProfiles(nextKey);
    updateProfilePreview();
  }

  function deleteProfile() {
    const select = document.getElementById('profiles');
    if (!select?.value) return;
    const name = select.value.slice(PROFILE_PREFIX.length);
    if (!window.confirm(`Profil „${name}“ löschen?`)) return;
    localStorage.removeItem(select.value);
    rebuildProfiles();
    updateProfilePreview();
  }

  function filterDisplay(filter, element) {
    if (!element) return '';
    if (element.tagName === 'SELECT') return selectedText(element);
    return `${element.value.trim()}${filter.suffix || ''}`;
  }

  function dispatchFilter(element) {
    const type = element.tagName === 'SELECT' ? 'change' : 'input';
    element.dispatchEvent(new Event(type, {bubbles: true}));
  }

  function updateActiveFilters() {
    const host = document.getElementById('active-result-filters');
    const count = document.getElementById('active-filter-count');
    if (!host) return;
    host.replaceChildren();
    let active = 0;
    for (const filter of FILTERS) {
      const element = document.getElementById(filter.id);
      if (!element || String(element.value) === filter.defaultValue) continue;
      active += 1;
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'active-filter-chip';
      chip.textContent = `${filter.label}: ${filterDisplay(filter, element)} ×`;
      chip.addEventListener('click', () => {
        element.value = filter.defaultValue;
        dispatchFilter(element);
        updateActiveFilters();
      });
      host.append(chip);
    }
    if (count) count.textContent = String(active);
  }

  function rerenderResults() {
    try {
      if (typeof activeState !== 'undefined' && activeState && typeof renderState === 'function') {
        activeState.renderLimit = 80;
        renderState(activeState, typeof activeWorker !== 'undefined' ? activeWorker : null);
      }
    } catch {
      // The search controller may still be loading; its own listeners will render later.
    }
  }

  function sourceStatusLabel(status) {
    return {
      idle: 'Noch nicht gestartet',
      active: 'Wird durchsucht',
      ok: 'Erfolgreich',
      empty: 'Keine Treffer',
      partial: 'Teilweise verfügbar',
      blocked: 'Momentan eingeschränkt',
      rate_limited: 'Kurzzeitig begrenzt',
      timeout: 'Zeitüberschreitung',
      unavailable: 'Momentan nicht erreichbar',
      disabled: 'Nicht ausgewählt'
    }[status] || 'Bereit';
  }

  function renderSourceProgress() {
    for (const source of ['kleinanzeigen', 'vinted', 'ebay']) {
      const row = document.querySelector(`[data-source-progress="${source}"]`);
      if (!row) continue;
      const state = sourceState.get(source) || {status: 'idle', count: 0};
      row.classList.remove('is-active', 'is-ok', 'is-degraded', 'is-disabled');
      if (state.status === 'active') row.classList.add('is-active');
      else if (['ok', 'empty'].includes(state.status)) row.classList.add('is-ok');
      else if (state.status === 'disabled') row.classList.add('is-disabled');
      else if (state.status !== 'idle') row.classList.add('is-degraded');
      row.querySelector('span:not(.source-progress-dot)').textContent = sourceStatusLabel(state.status);
      row.querySelector('b').textContent = String(state.count || 0);
    }
  }

  function resetSourceProgress(active = true) {
    const selected = document.getElementById('search-source')?.value || 'auto';
    for (const source of ['kleinanzeigen', 'vinted', 'ebay']) {
      const enabled = selected === 'auto' || selected === source;
      sourceState.set(source, {status: enabled ? (active ? 'active' : 'idle') : 'disabled', count: 0, keys: new Set()});
    }
    renderSourceProgress();
  }

  function updateSourceProgress(event) {
    const detail = event.detail || {};
    const source = detail.source;
    if (!source || !['kleinanzeigen', 'vinted', 'ebay'].includes(source)) return;
    const previous = sourceState.get(source) || {count: 0, keys: new Set()};
    const keys = previous.keys instanceof Set ? previous.keys : new Set();
    const listingKeys = Array.isArray(detail.listingKeys) ? detail.listingKeys : null;
    if (listingKeys) {
      for (const key of listingKeys) if (key) keys.add(String(key));
    }
    sourceState.set(source, {
      status: detail.status || 'ok',
      count: listingKeys ? keys.size : Number(previous.count || 0) + Number(detail.count || 0),
      keys
    });
    renderSourceProgress();
  }

  function install() {
    TERM_FIELDS.forEach(enhanceTermField);
    renderRecent();
    rebuildProfiles(document.getElementById('profiles')?.value || '');
    updateProfilePreview();
    updateCriteriaCount();
    updateSearchSummary();
    updateActiveFilters();
    renderSourceProgress();

    document.getElementById('query')?.addEventListener('input', updateSearchSummary);
    document.getElementById('query')?.addEventListener('keydown', event => {
      if (event.key === 'Enter') {
        event.preventDefault();
        document.getElementById('search-button')?.click();
      }
    });
    document.getElementById('search-source')?.addEventListener('change', () => {
      updateSearchSummary();
      resetSourceProgress(false);
    });
    for (const id of ['max-price', 'postal-code', 'location-id', 'radius-km', 'max-results']) {
      document.getElementById(id)?.addEventListener('input', () => {
        updateCriteriaCount();
        updateSearchSummary();
      });
    }
    for (const id of ['accept-bundles', 'accept-incomplete', 'include-ebay-auctions']) {
      document.getElementById(id)?.addEventListener('change', updateCriteriaCount);
    }

    document.getElementById('search-button')?.addEventListener('click', () => {
      saveRecent();
      resetSourceProgress();
      updateSearchSummary();
    }, {capture: true});
    document.getElementById('profiles')?.addEventListener('change', () => queueMicrotask(() => {
      syncEditors();
      updateProfilePreview();
      updateCriteriaCount();
      updateSearchSummary();
    }));
    document.getElementById('save-profile')?.addEventListener('click', () => queueMicrotask(() => {
      const name = document.getElementById('profile-name')?.value.trim() || 'Meine Suche';
      const key = PROFILE_PREFIX + name;
      try {
        const saved = JSON.parse(localStorage.getItem(key) || '{}');
        saved['search-source'] = document.getElementById('search-source')?.value || 'auto';
        localStorage.setItem(key, JSON.stringify(saved));
      } catch {}
      rebuildProfiles(key);
      updateProfilePreview();
    }));
    document.getElementById('rename-profile')?.addEventListener('click', renameProfile);
    document.getElementById('delete-profile')?.addEventListener('click', deleteProfile);

    for (const filter of FILTERS) {
      const element = document.getElementById(filter.id);
      element?.addEventListener(element?.tagName === 'SELECT' ? 'change' : 'input', () => {
        updateActiveFilters();
        rerenderResults();
      });
    }
    document.getElementById('reset-result-filters')?.addEventListener('click', () => queueMicrotask(() => {
      for (const filter of FILTERS) {
        const element = document.getElementById(filter.id);
        if (element) element.value = filter.defaultValue;
      }
      updateActiveFilters();
      rerenderResults();
    }));
    document.getElementById('mobile-filter-toggle')?.addEventListener('click', event => {
      const panel = document.getElementById('result-filters');
      const open = !panel?.classList.contains('is-open');
      panel?.classList.toggle('is-open', open);
      event.currentTarget.setAttribute('aria-expanded', String(open));
    });
    window.addEventListener('gp-source-status', updateSourceProgress);
    window.addEventListener('gp-chip-sync', syncEditors);

    const count = document.getElementById('results-count');
    if (count) new MutationObserver(updateSearchSummary).observe(count, {childList: true, characterData: true, subtree: true});
    const searchButton = document.getElementById('search-button');
    if (searchButton) new MutationObserver(() => {
      if (!searchButton.disabled && searchButton.textContent.trim() === 'Live-Suche starten') searchButton.textContent = 'Suchen';
    }).observe(searchButton, {childList: true, characterData: true, subtree: true, attributes: true, attributeFilter: ['disabled']});
  }

  window.GPUI160 = {parseTermList, searchSnapshot};
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once: true});
  else install();
})();
