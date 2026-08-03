(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');

  // Controlled rollback: use the last proven 0.42.9 controller flow without a
  // separate startup handshake. The controller may start immediately; identity
  // is still verified on every real /api/search response.
  window.GP_HANDSHAKE_READY = true;

  const sourceUrl = new URL('./controller-0411.js?v=0.433-stable-source', location.href);
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
      Function(`${source}\n//# sourceURL=controller-0433-runtime.js`)();
      const button = document.getElementById('search-button');
      if (button) {
        button.disabled = false;
        button.textContent = 'Live-Suche starten';
      }
      const connection = document.getElementById('connection');
      if (connection) {
        connection.classList.remove('offline');
        connection.innerHTML = '<span></span> Bereit';
      }
      const state = document.getElementById('worker-state-text');
      if (state) {
        state.className = 'diagnostic done';
        state.innerHTML = '<span><strong>Suchcontroller bereit</strong></span><span>Versionsprüfung erfolgt beim ersten Suchrequest.</span>';
      }
      window.GP_CONTROLLER_IDENTITY = {version: I.version, buildId: I.buildId, apiContract: I.apiContract, module: 'controller-0433.js'};
      window.dispatchEvent(new CustomEvent('gp-controller-ready', {detail: window.GP_CONTROLLER_IDENTITY}));
    })
    .catch(error => {
      window.GP_HANDSHAKE_READY = false;
      const button = document.getElementById('search-button');
      if (button) {
        button.disabled = true;
        button.textContent = 'Live-Suche gesperrt';
      }
      const state = document.getElementById('worker-state-text');
      if (state) {
        state.className = 'diagnostic error';
        state.textContent = `Controller konnte nicht geladen werden: ${error.message || error}`;
      }
    });
})();
