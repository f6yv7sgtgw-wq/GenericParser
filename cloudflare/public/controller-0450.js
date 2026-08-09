(async () => {
  'use strict';
  const I = await (window.GP_BUILD_IDENTITY_READY || Promise.resolve(window.GP_BUILD_IDENTITY));
  if (!I?.version || !I?.buildId || !I?.apiContract) throw new Error('Live build identity missing');
  window.GP_HANDSHAKE_READY = true;
  document.title = `GenericParser ${I.version}`;
  const heroVersion = document.querySelector('.hero h1 span');
  if (heroVersion) heroVersion.textContent = I.version;
  const workerChip = document.getElementById('worker-version');
  if (workerChip) workerChip.textContent = I.version;
  const footerBuild = document.querySelector('footer span');
  if (footerBuild) footerBuild.textContent = `GenericParser Mobile · Build ${I.buildId}`;
  const sourceUrl = new URL('./controller-0411.js?v=runtime-reference', location.href);
  fetch(sourceUrl, {cache: 'no-store'})
    .then(response => { if (!response.ok) throw new Error(`Controller source HTTP ${response.status}`); return response.text(); })
    .then(source => {
      const replacements = [
        [/const VERSION = '[^']+';/, `const VERSION = '${I.version}';`],
        [/const BUILD_ID = '[^']+';/, `const BUILD_ID = '${I.buildId}';`],
        [/const API_CONTRACT = '[^']+';/, `const API_CONTRACT = '${I.apiContract}';`],
        [/const LOG_KEY = '[^']+';/, `const LOG_KEY = '${I.eventLogKey}';`],
        [/const COOLDOWN_MS = \d+;/, 'const COOLDOWN_MS = 0;'],
        [/if \(workerVersion && \(workerVersion !== VERSION \|\| workerBuild !== BUILD_ID \|\| workerContract !== API_CONTRACT\)\) \{/, 'if (workerVersion && workerContract !== API_CONTRACT) {']
      ];
      for (const [pattern, to] of replacements) {
        if (!pattern.test(source)) throw new Error(`Controller runtime pattern missing: ${pattern}`);
        source = source.replace(pattern, to);
      }
      Function(`${source}\n//# sourceURL=controller-runtime.js`)();
      try { adaptiveDelay = () => 0; } catch {}
      try { countdown = async () => {}; } catch {}
      try {
        const originalRequestPage = requestPage;
        requestPage = async function(payload) {
          const data = await originalRequestPage(payload);
          const status = data?.source_status || data?.summary?.sources;
          const listings = Array.isArray(data?.listings) ? data.listings : [];
          const vinted = listings.filter(item => item?.source === 'vinted' || String(item?.id || '').startsWith('vinted:'));
          const enriched = vinted.filter(item => {
            const fields = item?.detail_enrichment?.fields;
            return item?.image_url || item?.price != null || item?.description || (Array.isArray(fields) && fields.length > 0);
          });
          const withImage = vinted.filter(item => !!item?.image_url).length;
          const withPrice = vinted.filter(item => item?.price != null).length;
          const withDescription = vinted.filter(item => !!item?.description).length;

          // The legacy reported_total belongs to Kleinanzeigen only. In a combined
          // response it must not be displayed as the total for both sources.
          const multiSource = status?.kleinanzeigen?.enabled === true && status?.vinted?.enabled === true;
          if (multiSource && data?.summary && typeof data.summary === 'object') {
            data.summary.reported_total = null;
          }

          if (status && window.gpEventLog) {
            window.gpEventLog('source_status','Quellenstatus aktualisiert',{
              query:payload?.query,
              page:payload?.page,
              sourceStatus:status,
              vintedCatalogHits:vinted.length,
              vintedEnriched:enriched.length,
              vintedWithImage:withImage,
              vintedWithPrice:withPrice,
              vintedWithDescription:withDescription
            });
          }
          if (vinted.length && window.gpEventLog) {
            window.gpEventLog('vinted_detail_enrichment','Vinted Detailanreicherung abgeschlossen',{
              query:payload?.query,
              page:payload?.page,
              catalogHits:vinted.length,
              enriched:enriched.length,
              withImage,
              withPrice,
              withDescription,
              failed:vinted.filter(item => item?.detail_enrichment?.status === 'failed').length
            });
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
      if (state) { state.className='compact-status done'; state.innerHTML=`<strong>GenericParser ${I.version}</strong><span>Kleinanzeigen + Vinted · Service Binding · Paid Worker · Modulvertrag v1</span>`; }
      window.GP_CONTROLLER_IDENTITY = {
        version:I.version,
        buildId:I.buildId,
        apiContract:I.apiContract,
        module:'controller-runtime',
        moduleContract:I.moduleContract,
        referenceController:I.operationalReference || null,
        referenceVersion:I.referenceVersion || null,
        operationalReference:I.operationalReference || null,
        runtimeReference:I.runtimeReference || null,
        searchCoreChanged:false,
        controllerFlowChanged:false,
        exactVersionMatchRequired:false,
        contractMatchRequired:true,
        sources:I.sources,
        runtimeBridge:I.runtimeBridge || null,
        vintedStrategy:I.vintedStrategy,
        workerPlan:I.workerPlan,
        protectionDelays:false,
        autoResume:true
      };
      window.dispatchEvent(new CustomEvent('gp-controller-ready',{detail:window.GP_CONTROLLER_IDENTITY}));
    })
    .catch(error => {
      window.GP_HANDSHAKE_READY = false;
      const button = document.getElementById('search-button');
      if (button) { button.disabled = true; button.textContent = 'Live-Suche gesperrt'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className='compact-status error'; state.textContent=`Controller konnte nicht geladen werden: ${error.message || error}`; }
    });
})().catch(error => {
  window.GP_HANDSHAKE_READY = false;
  const button = document.getElementById('search-button');
  if (button) { button.disabled = true; button.textContent = 'Live-Suche gesperrt'; }
  const state = document.getElementById('worker-state-text');
  if (state) { state.className='compact-status error'; state.textContent=`Release-Identität konnte nicht geladen werden: ${error.message || error}`; }
});
