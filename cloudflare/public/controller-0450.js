(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');
  window.GP_HANDSHAKE_READY = true;
  document.title = `GenericParser ${I.version}`;
  const heroVersion = document.querySelector('.hero h1 span');
  if (heroVersion) heroVersion.textContent = I.version;
  const workerChip = document.getElementById('worker-version');
  if (workerChip) workerChip.textContent = I.version;
  const footerBuild = document.querySelector('footer span');
  if (footerBuild) footerBuild.textContent = `GenericParser Mobile · Build ${I.buildId}`;
  const sourceUrl = new URL('./controller-0411.js?v=1.1.1-runtime-bridge-reference-source', location.href);
  fetch(sourceUrl, {cache: 'no-store'})
    .then(response => { if (!response.ok) throw new Error(`Controller source HTTP ${response.status}`); return response.text(); })
    .then(source => {
      const replacements = [
        ["const VERSION = '0.41.1';", `const VERSION = '${I.version}';`],
        ["const BUILD_ID = 'gp-0411-20260802-1';", `const BUILD_ID = '${I.buildId}';`],
        ["const API_CONTRACT = 'match-v6.1-page-worker';", `const API_CONTRACT = '${I.apiContract}';`],
        ["const LOG_KEY = 'generic-parser-eventlog-0411';", `const LOG_KEY = '${I.eventLogKey}';`],
        ["const COOLDOWN_MS = 2000;", "const COOLDOWN_MS = 0;"],
        ["if (workerVersion && (workerVersion !== VERSION || workerBuild !== BUILD_ID || workerContract !== API_CONTRACT)) {", "if (workerVersion && (workerContract !== API_CONTRACT || !['1.1','1.0','0.45'].includes(workerVersion.split('.').slice(0,2).join('.')))) {"]
      ];
      for (const [from, to] of replacements) {
        if (!source.includes(from)) throw new Error(`Controller constant missing: ${from}`);
        source = source.replace(from, to);
      }
      Function(`${source}\n//# sourceURL=controller-111-runtime-bridge.js`)();
      try { adaptiveDelay = () => 0; } catch {}
      try { countdown = async () => {}; } catch {}
      try {
        const originalRequestPage = requestPage;
        requestPage = async function(payload) {
          const data = await originalRequestPage(payload);
          const status = data?.source_status || data?.summary?.sources;
          if (status && window.gpEventLog) {
            window.gpEventLog('source_status', 'Quellenstatus aktualisiert', {query:payload?.query,page:payload?.page,sourceStatus:status});
          }
          return data;
        };
      } catch {}
      try {
        requestWithBackoff = async function(payload, s) {
          let last;
          for (let i = 0; i < 4; i++) {
            if (stopRequested) throw new Error('Suche wurde gestoppt.');
            if (i) s.retries++;
            try { return await requestPage(payload); }
            catch (e) {
              last = e;
              if (!e.retryable || [400,401,422].includes(e.status)) break;
              workerState('Worker wiederholt sofort', `Seite ${s.page+1} fehlgeschlagen · unmittelbarer Retry ${i+1}/4`, 'working');
            }
          }
          throw last;
        };
      } catch {}
      const delay = document.getElementById('page-delay');
      if (delay) { delay.disabled = true; delay.innerHTML = '<option value="0" selected>0 Sekunden · Paid Worker</option>'; delay.value = '0'; }
      const button = document.getElementById('search-button');
      if (button) { button.disabled = false; button.textContent = 'Live-Suche starten'; }
      const connection = document.getElementById('connection');
      if (connection) { connection.classList.remove('offline'); connection.innerHTML = '<span></span> Bereit'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className = 'compact-status done'; state.innerHTML = `<strong>GenericParser ${I.version}</strong><span>Kleinanzeigen + Vinted · Paid Worker · Runtime-Bridge 0.45 · Modulvertrag v1</span>`; }
      window.GP_CONTROLLER_IDENTITY = {version:I.version,buildId:I.buildId,apiContract:I.apiContract,module:'controller-0450.js',moduleContract:I.moduleContract,referenceController:'0.44.6.5',referenceVersion:'0.44.4',operationalReference:'0.44.6.5',runtimeReference:'0.44.6.2',searchCoreChanged:false,controllerFlowChanged:false,compatibleReleaseLines:['1.1','1.0','0.45'],sources:['kleinanzeigen','vinted'],runtimeBridge:'0.45.0',workerPlan:'paid',protectionDelays:false,autoResume:true};
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
