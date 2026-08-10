(() => {
  'use strict';

  const VERSION = '0.41.1';
  const BUILD_ID = 'gp-0411-20260802-1';
  const API_CONTRACT = 'match-v6.1-page-worker';
  const LOG_KEY = 'generic-parser-eventlog-0411';
  const MAX_LOG = 400;
  const COOLDOWN_MS = 2000;
  const nativeFetch = window.fetch.bind(window);

  let activeRun = null;
  let activeQuery = '';
  let activeSessionId = '';
  let stopping = false;
  let cooldownUntil = 0;
  let generation = 0;
  let requestSequence = 0;

  const now = () => new Date().toISOString();
  const safeJson = value => { try { return JSON.parse(value); } catch { return null; } };
  const log = (type, message, data = {}) => {
    try {
      const rows = safeJson(localStorage.getItem(LOG_KEY) || '[]') || [];
      const last = rows.at(-1);
      const signature = JSON.stringify([type, message, data.sessionId, data.requestId, data.query, data.page, data.status, data.phase, data.rayId]);
      if (last?.signature === signature && Date.now() - Number(last.epoch || 0) < 1000) return;
      rows.push({time: now(), epoch: Date.now(), type, message, uiVersion: VERSION, uiBuild: BUILD_ID, ...data, signature});
      localStorage.setItem(LOG_KEY, JSON.stringify(rows.slice(-MAX_LOG)));
    } catch (error) { console.warn('Eventlog konnte nicht geschrieben werden', error); }
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
    searchButton.disabled = running || window.GP_HANDSHAKE_READY !== true;
    searchButton.textContent = running ? 'Suche läuft …' : window.GP_HANDSHAKE_READY === true ? 'Live-Suche starten' : 'Live-Suche gesperrt';
    stopButton.classList.toggle('hidden', !running);
    stopButton.disabled = false;
    stopButton.textContent = 'Suche stoppen';
  }

  async function cooldown() {
    const remaining = Math.max(0, cooldownUntil - Date.now());
    if (!remaining) return;
    searchButton.disabled = true;
    workerState('Abkühlpause', `Neue Suche startet in ${(remaining / 1000).toFixed(1).replace('.', ',')} Sekunden.`, 'working');
    log('cooldown', 'Abkühlpause vor neuer Suche', {sessionId: activeSessionId, remainingMs: remaining});
    await new Promise(resolve => setTimeout(resolve, remaining));
    searchButton.disabled = window.GP_HANDSHAKE_READY !== true;
  }

  async function stopCurrent(reason = 'user_stopped') {
    if (!activeRun) return;
    if (!stopping) {
      stopping = true;
      stopRequested = true;
      stopButton.disabled = true;
      stopButton.textContent = 'Aktuelle Seite wird beendet …';
      workerState('Stopp angefordert', 'Die aktuelle Seite wird kontrolliert abgeschlossen.', 'working');
      log('stop_requested', 'Sanfter Stopp angefordert', {sessionId: activeSessionId, query: activeQuery, reason});
    }
    try { await activeRun; }
    catch (error) { log('stop_completion_error', 'Suchlauf endete während des Stopps', {sessionId: activeSessionId, query: activeQuery, name: error?.name, message: error?.message}); }
    activeRun = null;
    stopping = false;
    cooldownUntil = Date.now() + COOLDOWN_MS;
    setControlsRunning(false);
    workerState('Suche pausiert', `Suche „${activeQuery}“ wurde manuell gestoppt. Der Stand ist gespeichert und fortsetzbar.`, 'done');
    msg(`Suche „${activeQuery}“ wurde gestoppt. Der gespeicherte Stand kann fortgesetzt werden.`);
    resumeButton?.classList.remove('hidden');
    resumeButton.disabled = window.GP_HANDSHAKE_READY !== true;
    log('search_stopped', 'Suchlauf manuell gestoppt', {sessionId: activeSessionId, query: activeQuery, reason, complete:false, resumable:true});
  }

  window.fetch = async function controlledFetch(input, init = {}) {
    const url = typeof input === 'string' ? input : input?.url || '';
    const isSearch = /\/api\/search(?:\?|$)/.test(url);
    if (!isSearch) return nativeFetch(input, init);

    if (window.GP_HANDSHAKE_READY !== true) {
      return new Response(JSON.stringify({detail:'Versions-Handshake fehlt.',retryable:false,error_type:'deployment_mismatch',phase:'client_handshake',worker:{version:VERSION,build_id:BUILD_ID,api_contract:API_CONTRACT}}), {status:409,headers:{'Content-Type':'application/json','X-GenericParser-Version':VERSION,'X-GenericParser-Build':BUILD_ID,'X-GenericParser-Contract':API_CONTRACT}});
    }

    const requestId = `${activeSessionId || 'no-session'}-r${++requestSequence}`;
    const payload = typeof init.body === 'string' ? safeJson(init.body) : null;
    const query = String(payload?.query || activeQuery || document.getElementById('query')?.value?.trim() || '');
    const page = Number(payload?.page ?? 0);
    const source = String(payload?.source || 'auto');
    const started = performance.now();
    const common = {sessionId: activeSessionId, requestId, query, page, displayPage: page + 1, source, endpointUrl: url};

    log('before_fetch', 'Vor Netzwerkaufruf', {...common, payload});
    try {
      const response = await nativeFetch(input, init);
      const elapsedMs = Math.round(performance.now() - started);
      const contentType = response.headers.get('content-type') || '';
      const contentLengthHeader = response.headers.get('content-length');
      const workerVersion = response.headers.get('X-GenericParser-Version') || null;
      const workerBuild = response.headers.get('X-GenericParser-Build') || null;
      const workerContract = response.headers.get('X-GenericParser-Contract') || null;
      const workerPhase = response.headers.get('X-GenericParser-Phase') || null;
      log('after_fetch', 'Netzwerkantwort erhalten', {...common,status:response.status,ok:response.ok,elapsedMs,contentType,contentLengthHeader,workerVersion,workerBuild,workerContract,phase:workerPhase});

      if (workerVersion && (workerVersion !== VERSION || workerBuild !== BUILD_ID || workerContract !== API_CONTRACT)) {
        log('deployment_mismatch', 'API-Antwort gehört zu einem anderen Build', {...common,workerVersion,workerBuild,workerContract});
        return new Response(JSON.stringify({detail:`Deployment inkonsistent: UI ${VERSION}/${BUILD_ID}, Worker ${workerVersion}/${workerBuild || 'unbekannt'}.`,retryable:false,error_type:'deployment_mismatch',phase:'response_identity',worker:{version:workerVersion,build_id:workerBuild,api_contract:workerContract}}), {status:409,headers:{'Content-Type':'application/json','X-GenericParser-Version':workerVersion,'X-GenericParser-Build':workerBuild || 'unknown','X-GenericParser-Contract':workerContract || 'unknown'}});
      }

      log('before_parse', 'Antwortkopie wird analysiert', {...common, status: response.status, contentType});
      const text = await response.clone().text();
      const responseBytes = new TextEncoder().encode(text).length;
      const parsed = safeJson(text);
      const isJson = parsed !== null;
      log('after_parse', 'Antwortanalyse abgeschlossen', {...common,status:response.status,responseBytes,isJson,hasListings:Array.isArray(parsed?.listings),listingCount:Array.isArray(parsed?.listings)?parsed.listings.length:null,nextPage:parsed?.pagination?.next_page??null,paginationSource:parsed?.pagination?.source??null,stopReason:parsed?.pagination?.stop_reason??null,reportedTotal:parsed?.summary?.reported_total??null,errorType:parsed?.error_type??null,errorPhase:parsed?.phase??workerPhase,rayId:parsed?.ray_id??null});

      if (!contentType.includes('application/json') && /Error\s*1101|Worker threw exception/i.test(text)) {
        const rayId = text.match(/Ray ID:\s*([a-f0-9]+)/i)?.[1] || null;
        log('worker_1101', 'Cloudflare Worker-Ausnahme vor ASGI', {...common,status:response.status,elapsedMs,responseBytes,phase:'runtime_before_asgi',rayId});
        return new Response(JSON.stringify({detail:`Cloudflare 1101 vor ASGI${rayId?` · Ray-ID ${rayId}`:''}`,retryable:false,error_type:'cloudflare_1101',phase:'runtime_before_asgi',ray_id:rayId,request_id:requestId,page,worker:{version:VERSION,build_id:BUILD_ID,api_contract:API_CONTRACT}}), {status:422,headers:{'Content-Type':'application/json; charset=utf-8','X-GenericParser-Version':VERSION,'X-GenericParser-Build':BUILD_ID,'X-GenericParser-Contract':API_CONTRACT}});
      }
      return response;
    } catch (error) {
      log('request_error', 'Netzwerk- oder Analysefehler', {...common,elapsedMs:Math.round(performance.now()-started),name:error?.name,message:error?.message});
      throw error;
    }
  };

  async function runControlled(state, resume = false) {
    if (window.GP_HANDSHAKE_READY !== true) { msg('Live-Suche gesperrt: Deployment-Handshake fehlt.', true); return; }
    if (activeRun) await stopCurrent('superseded');
    await cooldown();
    resetView();
    stopRequested = false;
    stopping = false;
    activeQuery = state?.base?.query || document.getElementById('query').value.trim();
    activeSessionId = `${Date.now().toString(36)}-${(++generation).toString(36)}`;
    requestSequence = 0;
    state.sessionId = activeSessionId;
    state.sessionQuery = activeQuery;
    document.getElementById('worker-version').textContent = VERSION;
    workerState('Neue Suche startet', `Session ${activeSessionId.slice(-6)} · ${activeQuery}`, 'working');
    log(resume?'search_resume':'search_start',resume?'Gespeicherte Suche fortgesetzt':'Neue Suche gestartet',{query:activeQuery,sessionId:activeSessionId});
    setControlsRunning(true);
    const promise = Promise.resolve(runSearch(state, resume));
    activeRun = promise;
    try { return await promise; }
    catch (error) { log('search_error','Suchlauf mit Fehler beendet',{sessionId:activeSessionId,query:activeQuery,name:error?.name,message:error?.message}); throw error; }
    finally {
      if (activeRun === promise) activeRun = null;
      if (!stopping) setControlsRunning(false);
      log('search_end','Suchlauf beendet',{sessionId:activeSessionId,query:activeQuery,stopped:Boolean(state.stopped),complete:Boolean(state.complete),reason:state.stopReason||'',pages:state.pages,requests:state.requests,results:state.items?.size??null});
    }
  }

  searchButton?.addEventListener('click', async event => {
    event.preventDefault();
    if (window.GP_HANDSHAKE_READY !== true || activeRun || stopping) return;
    clearMessage();
    const base = baseBody();
    if (!base.query) { msg('Bitte einen Suchbegriff eingeben.', true); return; }
    const state = newState(base);
    await persist(state);
    try { await runControlled(state, false); } catch {}
  });

  stopButton?.addEventListener('click', async event => { event.preventDefault(); await stopCurrent('user_stopped'); });

  resumeButton?.addEventListener('click', async event => {
    event.preventDefault();
    if (window.GP_HANDSHAKE_READY !== true || activeRun || stopping) return;
    const raw = await dbGet();
    if (!raw) { msg('Kein gespeicherter Suchstand vorhanden.', true); return; }
    const state = restored(raw);
    state.pageLimit = Math.min(500, Number(state.pages || 0) + Number(document.getElementById('search-scope').value || 20));
    state.stopped = false; state.paused = false; state.complete = false;
    Object.entries(state.base || {}).forEach(([key, value]) => {
      const map={query:'query',postal_code:'postal-code',location_id:'location-id',radius_km:'radius-km',max_price:'max-price',market_value:'market-value',required_terms:'required-terms',excluded_terms:'excluded-terms',model_patterns:'model-patterns',brands:'brands'};
      const field=document.getElementById(map[key]); if(field) field.value=Array.isArray(value)?value.join(', '):value;
    });
    try { await runControlled(state, true); } catch {}
  });

  window.addEventListener('error', event => log('browser_error', event.message, {sessionId:activeSessionId,file:event.filename,line:event.lineno,column:event.colno}));
  window.addEventListener('unhandledrejection', event => log('promise_rejection', String(event.reason?.message || event.reason), {sessionId:activeSessionId}));
  window.addEventListener('beforeunload', () => { if(activeRun) log('page_unload','Seite während laufender Suche verlassen',{sessionId:activeSessionId,query:activeQuery}); });
})();
