(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');
  window.GP_HANDSHAKE_READY = true;
  const sourceUrl = new URL('./controller-0411.js?v=0.44661-reference-source', location.href);
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

      // Identical controller flow to the stable 0.44.6.5 reference. Cooldown
      // and recovery-control tests remain isolated and fail-open.
      Function(`${source}\n//# sourceURL=controller-044661-runtime.js`)();
      const button = document.getElementById('search-button');
      if (button) { button.disabled = false; button.textContent = 'Live-Suche starten'; }
      const connection = document.getElementById('connection');
      if (connection) { connection.classList.remove('offline'); connection.innerHTML = '<span></span> Bereit'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className = 'compact-status done'; state.innerHTML = '<strong>Bereit</strong><span>0.44.6.5-Suche aktiv · 120 Sekunden Pause bei 120, 240, 360 … Treffern</span>'; }
      const toggle = document.getElementById('technical-toggle');
      const technical = document.getElementById('technical-content');
      if (toggle && technical) toggle.onclick = () => { const open = technical.classList.toggle('open'); toggle.setAttribute('aria-expanded', String(open)); toggle.textContent = open ? 'Technische Details schließen' : 'Technische Details anzeigen'; };
      window.GP_CONTROLLER_IDENTITY = {version:I.version,buildId:I.buildId,apiContract:I.apiContract,module:'controller-04466.js',referenceController:'0.44.6.5',referenceVersion:'0.44.4',operationalReference:'0.44.6.5',runtimeReference:'0.44.6.2',searchCoreChanged:false,controllerFlowChanged:false,autoResume:true,recoveryControlFix:true,testCooldown:Boolean(window.GP_COOLDOWN_IDENTITY),cooldownStep:120,cooldownDurationMs:120000,cooldownMode:'repeated-multiples-fail-open'};
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
