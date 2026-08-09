(() => {
  'use strict';

  const BATCH_SIZE = 3;
  const REQUIRED_FIELDS = ['image', 'price', 'description'];
  let installed = false;
  let generation = 0;
  let runKey = '';
  let queue = [];
  let running = false;
  let activeBatchSize = 0;
  let controller = null;
  let totalQueued = 0;
  let attempted = 0;
  let failed = 0;
  let cancelled = 0;
  let stopped = false;
  const seen = new Set();
  const queued = new Set();
  const processed = new Set();
  const complete = new Set();
  const unavailable = new Set();
  const pendingUpdates = new Map();

  const log = (type, message, data = {}) => window.gpEventLog?.(type, message, data);
  const listingId = item => String(item?.id || '');
  const isVinted = item => item?.source === 'vinted' || listingId(item).startsWith('vinted:');
  const isComplete = item => Boolean(item?.image_url && item?.price != null && item?.description);
  const safeSearch = payload => {
    const copy = {...(payload || {})};
    delete copy.html;
    return copy;
  };

  function reset(run) {
    generation += 1;
    controller?.abort();
    controller = null;
    runKey = run;
    queue = [];
    running = false;
    activeBatchSize = 0;
    totalQueued = 0;
    attempted = 0;
    failed = 0;
    cancelled = 0;
    stopped = false;
    seen.clear();
    queued.clear();
    processed.clear();
    complete.clear();
    unavailable.clear();
    pendingUpdates.clear();
    renderProgress();
  }

  function renderProgress() {
    const section = document.getElementById('vinted-detail-state');
    const text = document.getElementById('vinted-detail-state-text');
    const chip = document.getElementById('vinted-detail-progress');
    if (!section || !text || !chip) return;
    if (!seen.size) {
      section.classList.add('hidden');
      return;
    }
    section.classList.remove('hidden');
    const pending = queue.length + activeBatchSize;
    const done = attempted;
    const full = complete.size;
    const terminal = pending === 0 && done + cancelled >= totalQueued;
    chip.textContent = `${full}/${seen.size}`;
    text.className = `compact-status ${terminal ? 'done' : 'working'}`;
    text.innerHTML = terminal
      ? `<strong>${stopped ? 'Vinted-Details nach Stopp beendet' : 'Vinted-Details abgeschlossen'}</strong><span>${full} vollständig · ${failed} unvollständig/fehlgeschlagen · ${cancelled} nicht mehr geladen · ${unavailable.size} ohne Detail-URL</span>`
      : `<strong>Vinted-Details werden nachgeladen</strong><span>${done}/${totalQueued} Hintergrundtreffer geprüft · ${pending} ausstehend · 3 parallel je Batch</span>`;
  }

  function mergeUpdate(existing, update) {
    const merged = {...existing, ...update};
    merged.result_info = {...(existing?.result_info || {}), ...(update?.result_info || {})};
    merged.detail_enrichment = {...(existing?.detail_enrichment || {}), ...(update?.detail_enrichment || {})};
    return merged;
  }

  function applyPending(state) {
    if (!state?.items || typeof state.items.has !== 'function') return false;
    let changed = false;
    for (const [id, update] of pendingUpdates) {
      if (!state.items.has(id)) continue;
      const merged = mergeUpdate(state.items.get(id), update);
      state.items.set(id, merged);
      pendingUpdates.delete(id);
      if (isComplete(merged)) complete.add(id);
      changed = true;
    }
    return changed;
  }

  function collect(listings, payload, {newRun = false} = {}) {
    const search = safeSearch(payload);
    const key = JSON.stringify(search, Object.keys(search).sort());
    if (newRun || !runKey) reset(key);
    for (const item of listings || []) {
      if (!isVinted(item)) continue;
      const id = listingId(item);
      if (!id) continue;
      seen.add(id);
      if (isComplete(item)) {
        complete.add(id);
        continue;
      }
      if (!item?.url) {
        unavailable.add(id);
        continue;
      }
      if (queued.has(id) || processed.has(id)) continue;
      queued.add(id);
      queue.push({listing: item, search});
      totalQueued += 1;
    }
    renderProgress();
    const token = generation;
    queueMicrotask(() => void drain(token));
  }

  async function requestBatch(batch, token) {
    let lastError;
    for (let attempt = 1; attempt <= 2; attempt += 1) {
      if (token !== generation) throw new DOMException('superseded', 'AbortError');
      controller = new AbortController();
      try {
        const response = await fetch(apiUrl('api/vinted/enrich'), {
          method: 'POST',
          headers: headers(),
          body: JSON.stringify({search: batch[0].search, listings: batch.map(row => row.listing)}),
          signal: controller.signal
        });
        const text = await response.text();
        let data = null;
        try { data = JSON.parse(text); } catch {}
        if (!response.ok || !data || !Array.isArray(data.listings)) {
          const error = new Error(data?.detail || `Vinted-Detailbatch HTTP ${response.status}`);
          error.status = response.status;
          throw error;
        }
        return data;
      } catch (error) {
        lastError = error;
        if (error?.name === 'AbortError' || attempt >= 2 || Number(error?.status) < 500) throw error;
        log('vinted_background_retry', 'Vinted-Hintergrundbatch wird unmittelbar wiederholt', {attempt, batchSize: batch.length, message: error?.message});
      }
    }
    throw lastError;
  }

  async function drain(token) {
    if (running || token !== generation) return;
    running = true;
    try {
      while (queue.length && token === generation) {
        if (typeof stopRequested !== 'undefined' && stopRequested) {
          log('vinted_background_cancelled', 'Vinted-Hintergrundanreicherung nach Stopp beendet', {remaining: queue.length});
          cancelled += queue.length;
          stopped = true;
          queue = [];
          queued.clear();
          break;
        }
        const batch = queue.splice(0, BATCH_SIZE);
        activeBatchSize = batch.length;
        renderProgress();
        const started = performance.now();
        log('vinted_background_batch_start', 'Vinted-Hintergrundbatch gestartet', {batchSize: batch.length, remaining: queue.length, ids: batch.map(row => listingId(row.listing))});
        try {
          const result = await requestBatch(batch, token);
          if (token !== generation) return;
          const updates = new Map(result.listings.map(item => [listingId(item), item]));
          for (const row of batch) {
            const id = listingId(row.listing);
            queued.delete(id);
            processed.add(id);
            attempted += 1;
            const update = updates.get(id);
            if (update) {
              pendingUpdates.set(id, update);
              if (isComplete(update)) complete.add(id);
              else failed += 1;
            } else {
              failed += 1;
            }
          }
          applyPending(typeof activeState !== 'undefined' ? activeState : null);
          if (typeof activeState !== 'undefined' && activeState) renderState(activeState, typeof activeWorker !== 'undefined' ? activeWorker : null);
          log('vinted_background_batch_end', 'Vinted-Hintergrundbatch abgeschlossen', {batchSize: batch.length, elapsedMs: Math.round(performance.now() - started), complete: Number(result.complete || 0), partial: Number(result.partial || 0), failed: Number(result.failed || 0), remaining: queue.length});
        } catch (error) {
          if (token !== generation || error?.name === 'AbortError') return;
          for (const row of batch) {
            const id = listingId(row.listing);
            queued.delete(id);
            processed.add(id);
            attempted += 1;
            failed += 1;
          }
          log('vinted_background_batch_error', 'Vinted-Hintergrundbatch fehlgeschlagen', {batchSize: batch.length, elapsedMs: Math.round(performance.now() - started), message: error?.message, remaining: queue.length});
        } finally {
          activeBatchSize = 0;
          controller = null;
          renderProgress();
        }
      }
    } finally {
      running = false;
      renderProgress();
      if (token === generation && !queue.length && totalQueued && !stopped) {
        log('vinted_background_complete', 'Vinted-Hintergrundanreicherung beendet', {seen: seen.size, queued: totalQueued, attempted, complete: complete.size, failed, cancelled, unavailable: unavailable.size, batchSize: BATCH_SIZE, mainSearchBlocked: false});
      }
    }
  }

  function install() {
    if (installed) return;
    if (typeof requestPage !== 'function' || typeof renderState !== 'function') return;
    installed = true;
    const originalRequestPage = requestPage;
    const originalRenderState = renderState;
    requestPage = async function(payload) {
      const data = await originalRequestPage(payload);
      collect(data?.listings, payload, {newRun: Number(payload?.page || 0) === 0});
      return data;
    };
    renderState = function(state, worker) {
      applyPending(state);
      const value = originalRenderState(state, worker);
      renderProgress();
      return value;
    };
    log('vinted_background_ready', 'Vinted-Hintergrundanreicherung bereit', {batchSize: BATCH_SIZE, requiredFields: REQUIRED_FIELDS, blocksMainSearch: false});
  }

  window.addEventListener('gp-controller-ready', install, {once: true});
  if (window.GP_CONTROLLER_IDENTITY) install();
})();
