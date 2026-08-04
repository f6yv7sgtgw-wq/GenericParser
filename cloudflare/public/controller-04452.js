(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');
  window.GP_HANDSHAKE_READY = true;
  const sourceUrl = new URL('./controller-0411.js?v=0.4452-stable-source', location.href);
  fetch(sourceUrl, {cache: 'no-store'})
    .then(response => { if (!response.ok) throw new Error(`Controller source HTTP ${response.status}`); return response.text(); })
    .then(source => {
      const replacements = [
        ["const VERSION = '0.41.1';", `const VERSION = '${I.version}';`],
        ["const BUILD_ID = 'gp-0411-20260802-1';", `const BUILD_ID = '${I.buildId}';`],
        ["const API_CONTRACT = 'match-v6.1-page-worker';", `const API_CONTRACT = '${I.apiContract}';`],
        ["const LOG_KEY = 'generic-parser-eventlog-0411';", `const LOG_KEY = '${I.eventLogKey}';`]
      ];
      for (const [from, to] of replacements) {
        if (!source.includes(from)) throw new Error(`Controller constant missing: ${from}`);
        source = source.replace(from, to);
      }
      Function(`${source}\n//# sourceURL=controller-04452-runtime.js`)();

      const CURSOR_KEY = 'generic-parser-cursors-04452';
      const safeJson = value => { try { return JSON.parse(value); } catch { return null; } };
      const loadCursors = () => safeJson(localStorage.getItem(CURSOR_KEY) || '{}') || {};
      const saveCursors = value => localStorage.setItem(CURSOR_KEY, JSON.stringify(value));
      let cursors = loadCursors();
      const controlledFetch = window.fetch.bind(window);

      window.fetch = async function cursorAwareFetch(input, init = {}) {
        const url = typeof input === 'string' ? input : input?.url || '';
        if (!/\/api\/search(?:\?|$)/.test(url)) return controlledFetch(input, init);
        const payload = typeof init.body === 'string' ? safeJson(init.body) : null;
        const page = Number(payload?.page ?? 0);
        const query = String(payload?.query || '').trim();
        const scope = JSON.stringify([query, payload?.postal_code || '', payload?.location_id || '', payload?.radius_km ?? '']);
        if (page === 0) {
          cursors[scope] = {};
          saveCursors(cursors);
        }
        const cursor = cursors[scope]?.[String(page)];
        let nextInit = init;
        if (payload && page > 0 && cursor && !payload.cursor_url) {
          const patched = {...payload, cursor_url: cursor, source: 'html-light-packets'};
          nextInit = {...init, body: JSON.stringify(patched)};
          window.gpEventLog?.('cursor_applied', 'Gespeicherte Weiter-URL angewendet', {query, page, cursorUrl: cursor});
        }
        const response = await controlledFetch(input, nextInit);
        try {
          const data = await response.clone().json();
          const pagination = data?.pagination || {};
          const nextPage = pagination.next_page;
          const nextCursor = pagination.cursor_url;
          if (nextPage != null && nextCursor) {
            cursors[scope] ||= {};
            cursors[scope][String(nextPage)] = nextCursor;
            saveCursors(cursors);
            window.gpEventLog?.('cursor_saved', 'Weiter-URL für nächsten Arbeitsschritt gespeichert', {query, page, nextPage, cursorUrl: nextCursor, cursorTransition:Boolean(pagination.cursor_transition)});
          }
          if (data?.coverage_diagnostics) {
            const d = data.coverage_diagnostics;
            window.gpEventLog?.('coverage_diagnostics', 'Extraktion, Preis und Pagination diagnostiziert', {
              query,
              page,
              schema:d.schema,
              extractionStrategy:d.extraction_strategy,
              candidateCards:d.candidate_card_count,
              navigationRemoved:d.navigation_candidates_removed,
              selectedCount:d.selected_range_count,
              extractedCount:d.extracted_count,
              priceRecognized:d.price_recognized_count,
              priceMissing:d.price_missing_count,
              actualSourceUrl:d.actual_source_url,
              cursorUrl:d.cursor_url,
              cursorNextPage:d.cursor_next_page,
              cursorTransition:d.cursor_transition,
              returnedIds:d.returned_ids
            });
          }
        } catch (error) {
          window.gpEventLog?.('diagnostic_parse_error', 'Zusatzdiagnose konnte nicht gelesen werden', {query, page, message:error?.message});
        }
        return response;
      };

      const button = document.getElementById('search-button');
      if (button) { button.disabled = false; button.textContent = 'Live-Suche starten'; }
      const connection = document.getElementById('connection');
      if (connection) { connection.classList.remove('offline'); connection.innerHTML = '<span></span> Bereit'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className = 'compact-status done'; state.innerHTML = '<strong>Bereit</strong><span>Echte Weiter-URL, Preis-Fallback und Diagnose aktiv</span>'; }
      const toggle = document.getElementById('technical-toggle');
      const technical = document.getElementById('technical-content');
      if (toggle && technical) toggle.onclick = () => { const open = technical.classList.toggle('open'); toggle.setAttribute('aria-expanded', String(open)); toggle.textContent = open ? 'Technische Details schließen' : 'Technische Details anzeigen'; };
      window.GP_CONTROLLER_IDENTITY = {version:I.version,buildId:I.buildId,apiContract:I.apiContract,module:'controller-04452.js',functionalReference:'0.44.4',runtimeModel:'direct-worker-stdlib-cursor-price-v1'};
      window.dispatchEvent(new CustomEvent('gp-controller-ready',{detail:window.GP_CONTROLLER_IDENTITY}));
    })
    .catch(error => {
      window.GP_HANDSHAKE_READY = false;
      const button = document.getElementById('search-button');
      if (button) { button.disabled = true; button.textContent = 'Live-Suche gesperrt'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className='compact-status error'; state.textContent=`Controller konnte nicht geladen werden: ${error.message || error}`; }
    });
})();
