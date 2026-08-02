(() => {
  'use strict';

  const VERSION = '0.40.7';
  const LOG_KEY = 'generic-parser-eventlog-0407';
  const MAX_LOG = 300;
  const COOLDOWN_MS = 2000;
  const nativeFetch = window.fetch.bind(window);

  let activeRun = null;
  let activeQuery = '';
  let stopping = false;
  let cooldownUntil = 0;
  let generation = 0;

  const now = () => new Date().toISOString();
  const log = (type, message, data = {}) => {
    try {
      const rows = JSON.parse(localStorage.getItem(LOG_KEY) || '[]');
      const last = rows.at(-1);
      const signature = JSON.stringify([type, message, data.query, data.page, data.status, data.phase, data.rayId]);
      if (last?.signature === signature && Date.now() - Number(last.epoch || 0) < 1500) return;
      rows.push({time: now(), epoch: Date.now(), type, message, ...data, signature});
      localStorage.setItem(LOG_KEY, JSON.stringify(rows.slice(-MAX_LOG)));
    } catch (error) {
      console.warn('Eventlog konnte nicht geschrieben werden', error);
    }
  };
  window.gpEventLog = log;

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

  function resetView() {
    document.getElementById('message').className = 'message hidden';
    document.getElementById('summary').classList.add('hidden');
    document.getElementById('diagnostics-card').classList.add('hidden');
    document.getElementById('results').innerHTML = '';
    document.getElementById('show-more').classList.add('hidden');
    activeState = null;
    activeWorker = null;
  }

  function setControlsRunning(running) {
    searchButton.disabled = running;
    searchButton.textContent = running ? 'Suche läuft …' : 'Live-Suche starten';
    stopButton.classList.toggle('hidden', !running);
    stopButton.disabled = false;
    stopButton.textContent = 'Suche stoppen';
  }

  async function cooldown() {
    const remaining = Math.max(0, cooldownUntil - Date.now());
    if (!remaining) return;
    searchButton.disabled = true;
    workerState('Abkühlpause', `Neue Suche startet in ${(remaining / 1000).toFixed(1).replace('.', ',')} Sekunden.`, 'working');
    log('cooldown', 'Abkühlpause vor neuer Suche', {remainingMs: remaining});
    await new Promise(resolve => setTimeout(resolve, remaining));
    searchButton.disabled = false;
  }

  async function stopCurrent(reason = 'user_stopped') {
    if (!activeRun) return;
    if (!stopping) {
      stopping = true;
      stopRequested = true;
      stopButton.disabled = true;
      stopButton.textContent = 'Aktuelle Seite wird beendet …';
      workerState('Stopp angefordert', 'Die aktuelle Seite wird kontrolliert abgeschlossen.', 'working');
      log('stop_requested', 'Sanfter Stopp angefordert', {query: activeQuery, reason});
    }
    try {
      await activeRun;
    } catch (error) {
      log('stop_completion_error', 'Suchlauf endete während des Stopps', {query: activeQuery, name: error?.name, message: error?.message});
    }
    activeRun = null;
    stopping = false;
    cooldownUntil = Date.now() + COOLDOWN_MS;
    setControlsRunning(false);
    workerState('Worker gestoppt', `Suche „${activeQuery}“ wurde vollständig beendet.`, 'done');
    msg(`Suche „${activeQuery}“ wurde gestoppt. Der gespeicherte Stand kann fortgesetzt werden.`);
    resumeButton?.classList.remove('hidden');
    log('search_stopped', 'Suchlauf vollständig beendet', {query: activeQuery});
  }

  window.fetch = async function controlledFetch(input, init = {}) {
    const url = typeof input === 'string' ? input : input?.url || '';
    const isSearch = /\/api\/search(?:\?|$)/.test(url);
    const query = document.getElementById('query')?.value?.trim() || activeQuery;
    const started = performance.now();
    if (isSearch) log('request_start', 'Seitenanfrage gestartet', {query, url});
    try {
      const response = await nativeFetch(input, init);
      if (isSearch) {
        const type = response.headers.get('content-type') || '';
        const elapsedMs = Math.round(performance.now() - started);
        if (!type.includes('application/json')) {
          const text = await response.clone().text();
          if (/Error\s*1101|Worker threw exception/i.test(text)) {
            const rayId = text.match(/Ray ID:\s*([a-f0-9]+)/i)?.[1] || null;
            log('worker_1101', 'Cloudflare Worker-Ausnahme vor ASGI', {query, status: response.status, elapsedMs, phase: 'runtime_before_asgi', rayId});
            return new Response(JSON.stringify({
              detail: `Cloudflare 1101 vor ASGI${rayId ? ` · Ray-ID ${rayId}` : ''}`,
              retryable: false,
              error_type: 'cloudflare_1101',
              phase: 'runtime_before_asgi',
              ray_id: rayId,
              worker: {version: VERSION}
            }), {status: 422, headers: {'Content-Type': 'application/json; charset=utf-8'}});
          }
        }
        log('request_end', 'Seitenanfrage beendet', {
          query,
          status: response.status,
          elapsedMs,
          phase: response.headers.get('X-GenericParser-Phase') || null,
          workerVersion: response.headers.get('X-GenericParser-Version') || null
        });
      }
      return response;
    } catch (error) {
      if (isSearch) log('request_error', 'Netzwerkfehler', {query, name: error?.name, message: error?.message});
      throw error;
    }
  };

  async function runControlled(state, resume = false) {
    if (activeRun) await stopCurrent('superseded');
    await cooldown();
    resetView();
    stopRequested = false;
    stopping = false;
    activeQuery = state?.base?.query || document.getElementById('query').value.trim();
    state.sessionId = `${Date.now().toString(36)}-${(++generation).toString(36)}`;
    state.sessionQuery = activeQuery;
    document.getElementById('worker-version').textContent = VERSION;
    workerState('Neue Suche startet', `Session ${state.sessionId.slice(-6)} · ${activeQuery}`, 'working');
    log(resume ? 'search_resume' : 'search_start', resume ? 'Gespeicherte Suche fortgesetzt' : 'Neue Suche gestartet', {query: activeQuery, sessionId: state.sessionId});
    setControlsRunning(true);
    const promise = Promise.resolve(runSearch(state, resume));
    activeRun = promise;
    try {
      return await promise;
    } catch (error) {
      log('search_error', 'Suchlauf mit Fehler beendet', {query: activeQuery, name: error?.name, message: error?.message});
      throw error;
    } finally {
      if (activeRun === promise) activeRun = null;
      if (!stopping) setControlsRunning(false);
      log('search_end', 'Suchlauf beendet', {query: activeQuery, stopped: Boolean(state.stopped), complete: Boolean(state.complete), reason: state.stopReason || ''});
    }
  }

  searchButton?.addEventListener('click', async event => {
    event.preventDefault();
    if (activeRun || stopping) return;
    clearMessage();
    const base = baseBody();
    if (!base.query) {
      msg('Bitte einen Suchbegriff eingeben.', true);
      return;
    }
    const state = newState(base);
    await persist(state);
    try { await runControlled(state, false); } catch {}
  });

  stopButton?.addEventListener('click', async event => {
    event.preventDefault();
    await stopCurrent('user_stopped');
  });

  resumeButton?.addEventListener('click', async event => {
    event.preventDefault();
    if (activeRun || stopping) return;
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
      const field = document.getElementById(map[key]);
      if (field) field.value = Array.isArray(value) ? value.join(', ') : value;
    });
    try { await runControlled(state, true); } catch {}
  });

  window.addEventListener('error', event => log('browser_error', event.message, {file: event.filename, line: event.lineno, column: event.colno}));
  window.addEventListener('unhandledrejection', event => log('promise_rejection', String(event.reason?.message || event.reason)));
  window.addEventListener('beforeunload', () => {
    if (activeRun) log('page_unload', 'Seite während laufender Suche verlassen', {query: activeQuery});
  });
})();
