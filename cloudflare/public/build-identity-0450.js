(() => {
  'use strict';

  const staticIdentity = {
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
    vintedBackgroundEnrichment: {enabled: true, endpoint: './api/vinted/enrich', batchSize: 3, serialBatches: true, blocksSearch: false},
    autoResume: {enabled: true, quietPeriodMs: 1, healthIntervalMs: 1, maxHealthChecks: 4, maxAutoResumes: 1},
    debug: {enabledByDefault: false, storageKey: 'generic-parser-debug', includePayload: false},
    tests: {enabledByDefault: false, storageKey: 'generic-parser-tests', endpoint: './api/module/v1/self-test?enabled=true', networkUsed: false}
  };

  window.GP_BUILD_IDENTITY_READY = (async () => {
    const response = await fetch('./health?identity=ui', {cache: 'no-store'});
    if (!response.ok) throw new Error(`Release identity HTTP ${response.status}`);
    const health = await response.json();
    const version = String(health.version || '').trim();
    const buildId = String(health.build_id || health.buildId || '').trim();
    const apiContract = String(health.api_contract || health.apiContract || '').trim();
    if (!version || !buildId || !apiContract) throw new Error('Live release identity incomplete');
    const identity = {
      ...staticIdentity,
      version,
      buildId,
      apiContract,
      moduleContract: String(health.module_contract || health.moduleContract || apiContract),
      referenceVersion: health.functional_reference || health.reference_version || null,
      operationalReference: health.operational_reference || null,
      runtimeReference: health.runtime_reference || null,
      runtimeBridge: health.search_runtime || health.runtime_bridge || null
    };
    window.GP_BUILD_IDENTITY = identity;
    return identity;
  })();
})();
