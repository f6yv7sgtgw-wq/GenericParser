(() => {
  'use strict';

  const originalRunSearch = runSearch;
  const originalFetch = window.fetch.bind(window);
  let activeRun = null;
  let activeController = null;
  let activeQuery = '';
  let generation = 0;

  const replaceButton = id => {
    const oldButton = document.getElementById(id);
    if (!oldButton) return null;
    const newButton = oldButton.cloneNode(true);
    oldButton.replaceWith(newButton);
    return newButton;
  };

  const searchButton = replaceButton('search-button');
  const stopButton = replaceButton('stop-button');
  const resumeButton = replaceButton('resume-button');

  const nextSessionId = () => `${Date.now().toString(36)}-${(++generation).toString(36)}`;

  window.fetch = function sessionFetch(input, init = {}) {
    const url = typeof input === 'string' ? input : input?.url || '';
    if (!activeController || !/\/api\/search(?:\?|$)/.test(url)) return originalFetch(input, init);
    return originalFetch(input, {...init, signal: activeController.signal});
  };

  async function endActive(reason) {
    if (!activeRun) return;
    stopRequested = true;
    activeController?.abort(reason);
    try { await activeRun; } catch {}
    activeRun = null;
    activeController = null;
  }

  function resetView() {
    document.getElementById('message').className = 'message hidden';
    document.getElementById('summary').classList.add('hidden');
    document.getElementById('diagnostics-card').classList.add('hidden');
    document.getElementById('results').innerHTML = '';
    document.getElementById('show-more').classList.add('hidden');
    activeState = null;
    activeWorker = null;
  }

  async function runIsolated(state, resume = false) {
    await endActive('superseded');
    resetView();
    stopRequested = false;
    const sessionId = nextSessionId();
    activeQuery = state?.base?.query || document.getElementById('query').value.trim();
    state.sessionId = sessionId;
    state.sessionQuery = activeQuery;
    activeController = new AbortController();
    document.getElementById('worker-version').textContent = '0.40.4';
    workerState('Neue Suche startet', `Session ${sessionId.slice(-6)} · ${activeQuery}`, 'working');
    const promise = Promise.resolve(originalRunSearch(state, resume));
    activeRun = promise;
    try {
      return await promise;
    } finally {
      if (activeRun === promise) {
        activeRun = null;
        activeController = null;
      }
    }
  }

  searchButton?.addEventListener('click', async () => {
    clearMessage();
    const base = baseBody();
    if (!base.query) {
      msg('Bitte einen Suchbegriff eingeben.', true);
      return;
    }
    const state = newState(base);
    await persist(state);
    await runIsolated(state, false);
  });

  stopButton?.addEventListener('click', async () => {
    const query = activeQuery;
    await endActive('user-stopped');
    searchButton.disabled = false;
    searchButton.textContent = 'Live-Suche starten';
    stopButton.classList.add('hidden');
    workerState('Worker gestoppt', `Suche „${query}“ wurde vollständig beendet.`, 'done');
    msg(`Suche „${query}“ wurde gestoppt. Der gespeicherte Stand kann fortgesetzt werden.`);
    resumeButton?.classList.remove('hidden');
  });

  resumeButton?.addEventListener('click', async () => {
    const raw = await dbGet();
    if (!raw) {
      msg('Kein gespeicherter Suchstand vorhanden.', true);
      return;
    }
    const state = restored(raw);
    state.pageLimit = Math.min(500, Number(state.pages || 0) + Number(document.getElementById('search-scope').value || 20));
    state.stopped = false;
    state.paused = false;
    state.complete = false;
    Object.entries(state.base || {}).forEach(([key, value]) => {
      const map = {query:'query',postal_code:'postal-code',location_id:'location-id',radius_km:'radius-km',max_price:'max-price',market_value:'market-value',required_terms:'required-terms',excluded_terms:'excluded-terms',model_patterns:'model-patterns',brands:'brands'};
      const id = map[key];
      const field = id && document.getElementById(id);
      if (field) field.value = Array.isArray(value) ? value.join(', ') : value;
    });
    await runIsolated(state, true);
  });

  window.addEventListener('beforeunload', () => activeController?.abort('page-unload'));
})();
