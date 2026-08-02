(() => {
  'use strict';

  const nativeFetch = window.fetch.bind(window);
  const originalRunSearch = window.runSearch;
  if (typeof originalRunSearch !== 'function') return;

  let activeRun = null;
  let activeController = null;
  let generation = 0;

  function sessionId() {
    generation += 1;
    return `${Date.now().toString(36)}-${generation.toString(36)}`;
  }

  async function cancelActive(reason = 'superseded') {
    if (!activeRun) return;
    try {
      window.stopRequested = true;
    } catch {}
    if (activeController && !activeController.signal.aborted) {
      activeController.abort(reason);
    }
    try {
      await activeRun;
    } catch {
      // The previous search may reject because its request was intentionally aborted.
    }
    activeRun = null;
    activeController = null;
  }

  window.fetch = function sessionFetch(input, init = {}) {
    const url = typeof input === 'string' ? input : input?.url || '';
    if (!activeController || !/\/api\/search(?:\?|$)/.test(url)) {
      return nativeFetch(input, init);
    }
    const merged = {...init, signal: activeController.signal};
    return nativeFetch(input, merged);
  };

  window.runSearch = async function sessionRunSearch(state, resume = false) {
    await cancelActive('new-search');

    const id = sessionId();
    activeController = new AbortController();
    state.sessionId = id;
    state.sessionQuery = state?.base?.query || '';

    const version = document.getElementById('worker-version');
    if (version) version.textContent = '0.40.2';
    const box = document.getElementById('worker-state-text');
    if (box) {
      box.className = 'diagnostic working';
      box.innerHTML = `<span><strong>Neue Suche startet</strong></span><span>Session ${id.slice(-6)} · ${state.sessionQuery || 'ohne Suchbegriff'}</span>`;
    }

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
  };

  const stopButton = document.getElementById('stop-button');
  stopButton?.addEventListener('click', () => {
    if (activeController && !activeController.signal.aborted) {
      activeController.abort('user-stopped');
    }
  }, true);

  const searchButton = document.getElementById('search-button');
  searchButton?.addEventListener('click', () => {
    if (activeRun) {
      try { window.stopRequested = true; } catch {}
      activeController?.abort('replaced-by-new-search');
    }
  }, true);

  window.addEventListener('beforeunload', () => {
    activeController?.abort('page-unload');
  });
})();
