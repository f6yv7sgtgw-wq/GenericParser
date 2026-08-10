(async () => {
  'use strict';
  const I = await (window.GP_BUILD_IDENTITY_READY || Promise.resolve(window.GP_BUILD_IDENTITY));
  if (!I?.version || !I?.buildId || !I?.apiContract) throw new Error('Live build identity missing');
  window.GP_HANDSHAKE_READY = true;
  document.title = `GenericParser ${I.version}`;
  document.querySelectorAll('[data-version]').forEach(node => { node.textContent = I.version; });
  const workerChip = document.getElementById('worker-version');
  if (workerChip) workerChip.textContent = I.version;
  const footerBuild = document.querySelector('footer span');
  if (footerBuild) footerBuild.textContent = `GenericParser Mobile · Build ${I.buildId}`;
  const sourceUrl = new URL('./controller-0411.js?v=runtime-reference', location.href);
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  const loadControllerSource = async () => {
    let lastError = null;
    for (const delay of [0, 250, 750]) {
      if (delay) await wait(delay);
      try {
        const response = await fetch(sourceUrl, {cache: 'no-store'});
        if (!response.ok) throw new Error(`Controller source HTTP ${response.status}`);
        const contentType = response.headers.get('content-type') || '';
        if (/text\/html/i.test(contentType)) throw new Error('Controller source returned HTML');
        return await response.text();
      } catch (error) {
        lastError = error;
      }
    }
    throw lastError || new Error('Controller source unavailable');
  };
  const directMode = error => {
    window.GP_HANDSHAKE_READY = true;
    const button = document.getElementById('search-button');
    if (button) { button.disabled = false; button.textContent = 'Live-Suche starten'; }
    const connection = document.getElementById('connection');
    if (connection) { connection.classList.remove('offline'); connection.classList.add('degraded'); connection.innerHTML = '<span></span> Bereit'; }
    const state = document.getElementById('worker-state-text');
    if (state) {
      state.className = 'compact-status done';
      state.innerHTML = '<strong>Bereit</strong><span>Die Suche ist verfügbar; die erweiterte Browserdiagnose wird später erneut geladen.</span>';
    }
    window.GP_CONTROLLER_IDENTITY = {
      version: I.version,
      buildId: I.buildId,
      apiContract: I.apiContract,
      module: 'browser-direct-fallback',
      moduleContract: I.moduleContract,
      preferredModuleContract: I.preferredModuleContract,
      webUiApiContract: I.webUiApiContract,
      degradedDiagnostics: true,
      diagnosticError: String(error?.message || error || 'Controller source unavailable'),
      searchCoreChanged: false,
      sources: I.sources
    };
    window.dispatchEvent(new CustomEvent('gp-controller-ready', {detail: window.GP_CONTROLLER_IDENTITY}));
  };
  loadControllerSource()
    .then(source => {
      const replacements = [
        [/const VERSION = '[^']+';/, `const VERSION = '${I.version}';`],
        [/const BUILD_ID = '[^']+';/, `const BUILD_ID = '${I.buildId}';`],
        [/const API_CONTRACT = '[^']+';/, `const API_CONTRACT = '${I.apiContract}';`],
        [/const LOG_KEY = '[^']+';/, `const LOG_KEY = '${I.eventLogKey}';`],
        [/const MAX_LOG = \d+;/, 'const MAX_LOG = 800;'],
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
        requestPage = async function(payload, state) {
          const data = await originalRequestPage(payload, state);
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
          const enabledSourceCount = ['kleinanzeigen','vinted','ebay'].filter(name => status?.[name]?.enabled === true).length;
          const multiSource = enabledSourceCount > 1;
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
              failed:vinted.filter(item => ['failed','error','blocked','empty','background_error'].includes(item?.detail_enrichment?.status)).length
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
            try { return await requestPage(payload, s); }
            catch (e) {
              last = e;
              if (!e.retryable || [400,401,409,410,422].includes(e.status)) break;
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
      if (state) { state.className='compact-status done'; state.innerHTML='<strong>Bereit</strong><span>Kleinanzeigen, Vinted und eBay sind verbunden.</span>'; }
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
        sourceOrchestrationChanged:true,
        controllerFlowChanged:false,
        exactVersionMatchRequired:false,
        contractMatchRequired:true,
        sources:I.sources,
        ebayStrategy:I.ebayStrategy,
        ebayPersistence:I.ebayPersistence,
        productClassification:I.productClassification,
        resultFilters:I.resultFilters,
        favoritesPage:I.favoritesPage,
        runtimeBridge:I.runtimeBridge || null,
        vintedStrategy:I.vintedStrategy,
        vintedBackgroundEnrichment:I.vintedBackgroundEnrichment,
        workerPlan:I.workerPlan,
        protectionDelays:false,
        autoResume:true
      };
      window.dispatchEvent(new CustomEvent('gp-controller-ready',{detail:window.GP_CONTROLLER_IDENTITY}));
    })
    .catch(error => {
      directMode(error);
    });
})().catch(error => {
  // Identity diagnostics are fail-open in 1.6.2. The static app controller can
  // still submit module-v2 requests and report a real API error if necessary.
  window.GP_HANDSHAKE_READY = true;
  const button = document.getElementById('search-button');
  if (button) { button.disabled = false; button.textContent = 'Live-Suche starten'; }
  const connection = document.getElementById('connection');
  if (connection) { connection.classList.remove('offline'); connection.classList.add('degraded'); connection.innerHTML = '<span></span> Bereit'; }
  const state = document.getElementById('worker-state-text');
  if (state) { state.className='compact-status done'; state.innerHTML='<strong>Bereit</strong><span>Die Live-Identität wird im Hintergrund erneut geprüft.</span>'; }
});
