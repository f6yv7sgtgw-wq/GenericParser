/* GenericParser 1.8.0 - Verhalten der modernen Suchmaske.
 *
 * Ergänzt zwei Dinge, ohne einen bestehenden Vertrag zu berühren:
 * die Plattformwahl als Segmentleiste über dem unveränderten <select>, und
 * Ladeplatzhalter, solange eine Suche läuft und noch keine Treffer da sind.
 */
(() => {
  'use strict';

  const SKELETON_COUNT = 6;
  let installed = false;

  function buildSourceSegments() {
    const select = document.getElementById('search-source');
    const field = select?.closest('.source-field');
    if (!select || !field || field.classList.contains('has-segments')) return;

    const group = document.createElement('div');
    group.className = 'source-segments';
    group.setAttribute('role', 'group');
    group.setAttribute('aria-label', 'Plattform');

    const buttons = Array.from(select.options).map(option => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'source-segment';
      button.textContent = option.textContent;
      button.dataset.value = option.value;
      button.addEventListener('click', () => {
        // Das <select> bleibt die Datenquelle; app.js liest weiterhin dort.
        select.value = option.value;
        select.dispatchEvent(new Event('change', {bubbles: true}));
        sync();
      });
      group.append(button);
      return button;
    });

    function sync() {
      for (const button of buttons) {
        button.setAttribute('aria-pressed', String(button.dataset.value === select.value));
      }
    }

    select.addEventListener('change', sync);
    field.append(group);
    field.classList.add('has-segments');
    sync();
  }

  function skeletonMarkup() {
    const card = '<div class="skeleton-card" aria-hidden="true">'
      + '<div class="skeleton-media"></div>'
      + '<div class="skeleton-lines"><span></span><span></span><span></span></div>'
      + '</div>';
    return `<div class="skeleton-grid">${card.repeat(SKELETON_COUNT)}</div>`;
  }

  function showSkeletons() {
    const results = document.getElementById('results');
    // Nur füllen, solange wirklich nichts da ist: ein laufender Folgeabruf darf
    // bereits gelieferte Treffer nicht verdecken.
    if (!results || results.children.length) return;
    results.innerHTML = skeletonMarkup();
  }

  function clearSkeletons() {
    const results = document.getElementById('results');
    if (results?.querySelector('.skeleton-grid')) results.innerHTML = '';
  }

  function install() {
    if (installed) return;
    installed = true;
    buildSourceSegments();
    window.addEventListener('gp-search-run-state', event => {
      if (event.detail?.running === false) clearSkeletons();
      else showSkeletons();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }

  window.GPUI180 = {buildSourceSegments, skeletonMarkup, showSkeletons, clearSkeletons};
})();
