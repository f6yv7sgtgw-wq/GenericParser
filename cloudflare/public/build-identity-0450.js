(() => {
  'use strict';

  // The release identity is embedded deliberately. A transient /health failure
  // must never lock the browser search. Live identity verification runs in the
  // background and updates this object in place when it succeeds.
  const identity = {
    version: '1.7.0',
    buildId: 'gp-170-20260812-1',
    apiContract: 'generic-parser-module-v1',
    moduleContract: 'generic-parser-module-v1',
    supportedModuleContracts: ['generic-parser-module-v1', 'generic-parser-module-v2'],
    preferredModuleContract: 'generic-parser-module-v2',
    webUiApiContract: 'generic-parser-module-v2',
    identitySource: 'embedded-release-fallback',
    identityVerified: false,
    eventLogKey: 'generic-parser-eventlog',
    diagnosticMode: 'multisource-service-binding-production',
    moduleRelease: true,
    searchCoreChanged: false,
    sourceOrchestrationChanged: true,
    exactVersionMatchRequired: false,
    contractMatchRequired: true,
    workerPlan: 'paid',
    protectionDelays: false,
    sources: ['kleinanzeigen', 'vinted', 'ebay'],
    defaultSources: ['kleinanzeigen', 'vinted', 'ebay'],
    ebayStrategy: 'official-browse-api',
    ebayPersistence: 'explicit-browser-favorites-only',
    productClassification: 'product-classification-v1',
    resultFilters: true,
    favoritesPage: './favorites.html',
    ebayDeletionEndpoint: 'https://genericparser-ebay-notifications.f6yv7sgtgw.workers.dev/marketplace-account-deletion',
    vintedStrategy: 'service-binding',
    vintedBackgroundEnrichment: {enabled: true, endpoint: './api/vinted/enrich', batchSize: 3, serialBatches: true, blocksSearch: false, yieldsToPrimarySearch: true},
    autoResume: {enabled: true, quietPeriodMs: 1, healthIntervalMs: 1, maxHealthChecks: 4, maxAutoResumes: 1},
    debug: {enabledByDefault: false, storageKey: 'generic-parser-debug', includePayload: false},
    tests: {enabledByDefault: false, storageKey: 'generic-parser-tests', endpoint: './api/module/v1/self-test?enabled=true', networkUsed: false}
  };

  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

  async function fetchJson(url, timeoutMs = 5000) {
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    const timeout = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
    try {
      const response = await fetch(url, {
        cache: 'no-store',
        headers: {Accept: 'application/json'},
        signal: controller?.signal
      });
      if (!response.ok) throw new Error(`Release identity HTTP ${response.status}`);
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) throw new Error('Release identity is not JSON');
      return await response.json();
    } finally {
      if (timeout) clearTimeout(timeout);
    }
  }

  function liveIdentity(health) {
    const version = String(health.version || '').trim();
    const buildId = String(health.build_id || health.buildId || '').trim();
    const apiContract = String(health.api_contract || health.apiContract || '').trim();
    if (!version || !buildId || !apiContract) throw new Error('Live release identity incomplete');
    return {
      version,
      buildId,
      apiContract,
      moduleContract: String(health.module_contract || health.moduleContract || apiContract),
      supportedModuleContracts: Array.isArray(health.supported_module_contracts) ? health.supported_module_contracts : [apiContract],
      preferredModuleContract: String(health.preferred_module_contract || health.preferredModuleContract || apiContract),
      webUiApiContract: String(health.web_ui_api_contract || health.webUiApiContract || apiContract),
      referenceVersion: health.functional_reference || health.reference_version || null,
      operationalReference: health.operational_reference || null,
      runtimeReference: health.runtime_reference || null,
      runtimeBridge: health.search_runtime || health.runtime_bridge || null,
      identitySource: 'live-health',
      identityVerified: true,
      identityVerifiedAt: new Date().toISOString()
    };
  }

  function publishStatus(ok, error = null) {
    const detail = {
      ok,
      identity,
      error: error ? String(error?.message || error) : null
    };
    window.GP_BUILD_IDENTITY_STATUS = detail;
    window.dispatchEvent(new CustomEvent('gp-identity-status', {detail}));
  }

  window.GP_BUILD_IDENTITY = identity;
  window.GP_BUILD_IDENTITY_READY = Promise.resolve(identity);
  window.GP_LIVE_IDENTITY_READY = (async () => {
    let lastError = null;
    for (const delay of [0, 300, 900]) {
      if (delay) await wait(delay);
      try {
        const health = await fetchJson(`./health?identity=ui&build=${encodeURIComponent(identity.buildId)}`);
        Object.assign(identity, liveIdentity(health));
        publishStatus(true);
        return identity;
      } catch (error) {
        lastError = error;
      }
    }
    identity.identityError = String(lastError?.message || lastError || 'Live-Prüfung nicht erreichbar');
    publishStatus(false, lastError);
    console.warn('Live-Identität konnte nicht geprüft werden; die Suche bleibt verfügbar.', lastError);
    return identity;
  })();
})();
