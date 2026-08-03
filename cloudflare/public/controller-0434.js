(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');
  window.GP_HANDSHAKE_READY = true;

  const sourceUrl = new URL('./controller-0411.js?v=0.434-stable-source', location.href);
  fetch(sourceUrl, {cache: 'no-store'})
    .then(response => {
      if (!response.ok) throw new Error(`Controller source HTTP ${response.status}`);
      return response.text();
    })
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
      Function(`${source}\n//# sourceURL=controller-0434-runtime.js`)();

      // Add one bounded evidence event per API response without changing the
      // proven controller or search state machine.
      const controlledFetch = window.fetch;
      window.fetch = async function evidenceFetch(input, init = {}) {
        const response = await controlledFetch(input, init);
        const url = typeof input === 'string' ? input : input?.url || '';
        if (/\/api\/search(?:\?|$)/.test(url)) {
          try {
            const data = await response.clone().json();
            if (data?.coverage_diagnostics) {
              window.gpEventLog?.('coverage_diagnostics', 'Trefferabdeckung der Quellseite', data.coverage_diagnostics);
            }
          } catch (_) {}
        }
        return response;
      };

      const button = document.getElementById('search-button');
      if (button) { button.disabled = false; button.textContent = 'Live-Suche starten'; }
      const connection = document.getElementById('connection');
      if (connection) { connection.classList.remove('offline'); connection.innerHTML = '<span></span> Bereit'; }
      const state = document.getElementById('worker-state-text');
      if (state) {
        state.className = 'diagnostic done';
        state.innerHTML = '<span><strong>Suchcontroller bereit</strong></span><span>Abdeckungsdiagnose wird pro Arbeitspaket protokolliert.</span>';
      }
      window.GP_CONTROLLER_IDENTITY = {version: I.version, buildId: I.buildId, apiContract: I.apiContract, module: 'controller-0434.js'};
      window.dispatchEvent(new CustomEvent('gp-controller-ready', {detail: window.GP_CONTROLLER_IDENTITY}));
    })
    .catch(error => {
      window.GP_HANDSHAKE_READY = false;
      const button = document.getElementById('search-button');
      if (button) { button.disabled = true; button.textContent = 'Live-Suche gesperrt'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className = 'diagnostic error'; state.textContent = `Controller konnte nicht geladen werden: ${error.message || error}`; }
    });
})();
