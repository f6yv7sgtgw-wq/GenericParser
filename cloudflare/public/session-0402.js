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

  function triggerOriginalStop() {
    const stopButton = document.getElementById('stop-button');
    if (stopButton && !stopButton.disabled) stopButton.click();
  }

  async function cancelActive(reason = 'superseded') {
    if (!activeRun) return;
    triggerOriginalStop();
    if (activeController && !activeController.signal.aborted) {
      activeController.abort(reason);
    }
    try {
      await activeRun;
    } catch {
      // Intentional cancellation may reject the old request.
    }
    activeRun = null;
    activeController = null;
  }

  window.fetch = function sessionFetch(input, init = {}) {
    const url = typeof input === 'string' ? input : input?.url || '';
    if (!activeController || !/\/api\/search(?:\?|$)/.test(url)) {
      return nativeFetch(input, init);
    }
    return nativeFetch(input, {...init, signal:activeController.signal});
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
    if (activeRun && activeController && !activeController.signal.aborted) {
      activeController.abort('replaced-by-new-search');
    }
  }, true);

  window.addEventListener('beforeunload', () => {
    activeController?.abort('page-unload');
  });
})();
