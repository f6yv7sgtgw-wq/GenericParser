(() => {
  'use strict';

  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');

  const cfg = I.autoResume || {};
  const options = {
    recoveryKey: String(cfg.recoveryKey || 'generic-parser-auto-resume-04463'),
    probeEndpoint: String(cfg.probeEndpoint || './api/recovery-probe'),
    backoffMs: Array.isArray(cfg.backoffMs) && cfg.backoffMs.length ? cfg.backoffMs.map(Number) : [90000, 180000, 360000],
    jitterRatio: Number.isFinite(Number(cfg.jitterRatio)) ? Number(cfg.jitterRatio) : 0.10,
    probeIntervalsMs: Array.isArray(cfg.probeIntervalsMs) && cfg.probeIntervalsMs.length ? cfg.probeIntervalsMs.map(Number) : [30000, 60000, 120000],
    maxProbeAttempts: Number(cfg.maxProbeAttempts || 3),
    maxAutoResumes: Number(cfg.maxAutoResumes || 2),
  };
  const MAX_PERSISTED_AGE_MS = 45 * 60 * 1000;
  const processed = new Set();
  let recovery = loadRecovery();
  let probeInFlight = false;
  let started = false;

  function readJson(key, fallback) {
    try {
      const value = JSON.parse(localStorage.getItem(key) || 'null');
      return value == null ? fallback : value;
    } catch {
      return fallback;
    }
  }

  function loadRecovery() {
    const value = readJson(options.recoveryKey, null);
    return value && typeof value === 'object' ? value : null;
  }

  function saveRecovery() {
    if (!recovery) {
      localStorage.removeItem(options.recoveryKey);
      return;
    }
    recovery.updatedAt = Date.now();
    localStorage.setItem(options.recoveryKey, JSON.stringify(recovery));
  }

  function readEvents() {
    const value = readJson(I.eventLogKey, []);
    return Array.isArray(value) ? value : [];
  }

  function signatureOf(event) {
    return String(event?.signature || JSON.stringify([
      event?.time,
      event?.type,
      event?.sessionId,
      event?.requestId,
      event?.page,
      event?.status,
      event?.reason,
      event?.message,
    ]));
  }

  function appendLog(type, message, data = {}) {
    const payload = {recoveryVersion: I.version, ...data};
    if (typeof window.gpEventLog === 'function') {
      window.gpEventLog(type, message, payload);
      return;
    }
    try {
      const rows = readEvents();
      const epoch = Date.now();
      rows.push({
        time: new Date(epoch).toISOString(),
        epoch,
        type,
        message,
        uiVersion: I.version,
        uiBuild: I.buildId,
        ...payload,
        signature: JSON.stringify([type, payload.sessionId, payload.failureSignature, epoch]),
      });
      localStorage.setItem(I.eventLogKey, JSON.stringify(rows.slice(-400)));
    } catch {}
  }

  function eventEpoch(event) {
    return Number(event?.epoch || Date.parse(event?.time) || 0);
  }

  function uniqueHtml503Count(session) {
    return new Set(
      session
        .filter(event => Number(event.status) === 503 && /text\/html/i.test(String(event.contentType || '')))
        .map(event => event.requestId || `${event.page || 0}:${event.time || ''}`)
    ).size;
  }

  function sessionEvidence(events, sessionId) {
    const session = events.filter(event => event.sessionId === sessionId);
    const errorTypes = session
      .map(event => String(event.cfErrorType || event.errorType || ''))
      .filter(Boolean);
    const has1101 = session.some(event => event.type === 'worker_1101' || errorTypes.includes('1101') || errorTypes.includes('cloudflare_1101'));
    const has1102 = session.some(event => errorTypes.includes('1102') || errorTypes.includes('cloudflare_1102'));
    const html503RequestCount = uniqueHtml503Count(session);
    const lastFailure = [...session].reverse().find(event =>
      event.type === 'worker_1101' ||
      Number(event.status) >= 500 ||
      event.cfErrorType ||
      event.errorType
    ) || null;
    return {
      has1101,
      has1102,
      html503RequestCount,
      recoverable: has1101 || has1102 || html503RequestCount >= 2,
      cfErrorType: lastFailure?.cfErrorType || lastFailure?.errorType || (has1101 ? '1101' : has1102 ? '1102' : null),
      cfErrorOrigin: lastFailure?.cfErrorOrigin || null,
      retryAfter: lastFailure?.retryAfter || null,
      rayId: lastFailure?.rayId || lastFailure?.responseRayId || null,
    };
  }

  function jittered(baseMs) {
    const spread = Math.max(0, baseMs * options.jitterRatio);
    return Math.max(1000, Math.round(baseMs - spread + Math.random() * spread * 2));
  }

  function cycleDelay(cycleIndex) {
    const index = Math.min(Math.max(0, cycleIndex), options.backoffMs.length - 1);
    return jittered(Number(options.backoffMs[index] || 90000));
  }

  function probeDelay(probeAttempt) {
    const index = Math.min(Math.max(0, probeAttempt), options.probeIntervalsMs.length - 1);
    return Number(options.probeIntervalsMs[index] || 30000);
  }

  function formatDuration(milliseconds) {
    const seconds = Math.max(0, Math.ceil(Number(milliseconds || 0) / 1000));
    if (seconds < 60) return `${seconds} s`;
    const minutes = Math.floor(seconds / 60);
    const rest = seconds % 60;
    return rest ? `${minutes} min ${rest} s` : `${minutes} min`;
  }

  function ensureRecoveryPanel() {
    let panel = document.getElementById('recovery-status-card');
    if (panel) return panel;
    panel = document.createElement('section');
    panel.id = 'recovery-status-card';
    panel.className = 'card hidden';
    const workerState = document.getElementById('worker-state');
    if (workerState?.parentNode) workerState.parentNode.insertBefore(panel, workerState.nextSibling);
    return panel;
  }

  function renderRecoveryPanel() {
    const panel = ensureRecoveryPanel();
    if (!panel) return;
    if (!recovery || ['idle', 'completed', 'cancelled', 'cleared'].includes(recovery.status)) {
      panel.classList.add('hidden');
      panel.innerHTML = '';
      return;
    }
    panel.classList.remove('hidden');
    const remaining = Math.max(0, Number(recovery.nextActionAt || 0) - Date.now());
    const attempts = Number(recovery.autoResumeCount || 0);
    const probeAttempts = Number(recovery.probeAttempt || 0);
    const successful = Number(recovery.successfulAutoResumes || 0);
    const statusLabel = {
      waiting: 'Ruhezeit',
      probing: 'Recovery-Probe',
      starting_auto: 'Fortsetzung startet',
      auto_running: 'Fortgesetzte Suche läuft',
      manual_required: 'Manuelle Fortsetzung erforderlich',
    }[recovery.status] || recovery.status || 'bereit';
    panel.innerHTML = `
      <div class="row between"><h2>Recovery</h2><span class="chip">${statusLabel}</span></div>
      <div class="diagnostic">
        <span>Auto-Resumes: ${attempts}/${options.maxAutoResumes}</span>
        <span>Erfolgreich gestartet: ${successful}</span>
        <span>Probe: ${probeAttempts}/${options.maxProbeAttempts}</span>
        <span>Nächste Aktion: ${remaining ? formatDuration(remaining) : 'jetzt'}</span>
        <span>Letzter Fehler: ${recovery.evidence?.cfErrorType || (recovery.evidence?.html503RequestCount ? `HTML 503 × ${recovery.evidence.html503RequestCount}` : '–')}</span>
        <span>Ray-ID: ${recovery.evidence?.rayId || '–'}</span>
        <span>Letzte Probe: ${recovery.lastProbeStatus || '–'}</span>
      </div>`;
  }

  function setStatus(title, detail, kind = 'working') {
    const state = document.getElementById('worker-state-text');
    if (state) {
      state.className = `compact-status ${kind}`;
      state.innerHTML = `<strong>${title}</strong><span>${detail}</span>`;
    }
    renderRecoveryPanel();
  }

  function showWaiting() {
    if (!recovery || !['waiting', 'probing'].includes(recovery.status)) return;
    const remaining = Math.max(0, Number(recovery.nextActionAt || 0) - Date.now());
    const cycle = Math.min(Number(recovery.autoResumeCount || 0) + 1, options.maxAutoResumes);
    if (recovery.status === 'probing') {
      setStatus(
        'Recovery-Probe vorbereitet',
        `Probe ${Number(recovery.probeAttempt || 0) + 1}/${options.maxProbeAttempts} in ${formatDuration(remaining)} · Auto-Resume ${cycle}/${options.maxAutoResumes}`
      );
    } else {
      setStatus(
        'Recovery aktiv',
        `Auto-Resume ${cycle}/${options.maxAutoResumes} in ${formatDuration(remaining)} · ${Number(recovery.results || 0)} Ergebnisse gespeichert`
      );
    }
    const message = document.getElementById('message');
    if (message) {
      message.className = 'message';
      message.textContent = 'Der Suchstand bleibt gespeichert. Nach der gestaffelten Ruhezeit wird der vollständige Suchpfad geprüft und anschließend automatisch fortgesetzt.';
    }
  }

  function requireManual(reason, detail) {
    if (!recovery) recovery = {};
    recovery.status = 'manual_required';
    recovery.manualReason = reason;
    recovery.nextActionAt = null;
    saveRecovery();
    appendLog('recovery_manual_required', 'Automatische Recovery beendet; manuelles Fortsetzen erforderlich', {
      sessionId: recovery.failureSessionId,
      reason,
      detail,
      autoResumeCount: Number(recovery.autoResumeCount || 0),
      results: Number(recovery.results || 0),
    });
    setStatus('Fortsetzung bereit', `${detail} · Suchstand gespeichert`, 'error');
    const message = document.getElementById('message');
    if (message) {
      message.className = 'message error';
      message.textContent = `${detail} Bitte „Letzte Suche fortsetzen“ verwenden.`;
    }
  }

  function resetForNewSearch(event) {
    recovery = {
      status: 'running',
      rootSessionId: event.sessionId,
      currentSessionId: event.sessionId,
      query: event.query || '',
      autoResumeCount: 0,
      successfulAutoResumes: 0,
      probeAttempt: 0,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    saveRecovery();
    renderRecoveryPanel();
  }

  function scheduleRecovery(endEvent, evidence) {
    const used = Number(recovery?.autoResumeCount || 0);
    if (used >= options.maxAutoResumes) {
      requireManual('auto_resume_limit_reached', 'Beide automatischen Fortsetzungsversuche wurden bereits verwendet.');
      return;
    }
    if (!recovery) {
      recovery = {
        rootSessionId: endEvent.sessionId,
        query: endEvent.query || '',
        autoResumeCount: 0,
        successfulAutoResumes: 0,
        createdAt: Date.now(),
      };
    }
    const failureSignature = `${endEvent.sessionId || 'session'}:${endEvent.results || 0}:${endEvent.reason || 'retry_exhausted'}:${used}`;
    if (recovery.failureSignature === failureSignature && ['waiting', 'probing', 'starting_auto'].includes(recovery.status)) return;
    const delayMs = cycleDelay(used);
    recovery.status = 'waiting';
    recovery.failureSessionId = endEvent.sessionId;
    recovery.currentSessionId = endEvent.sessionId;
    recovery.failureSignature = failureSignature;
    recovery.results = Number(endEvent.results || 0);
    recovery.pages = Number(endEvent.pages || 0);
    recovery.requests = Number(endEvent.requests || 0);
    recovery.probeAttempt = 0;
    recovery.evidence = evidence;
    recovery.recoveryDelayMs = delayMs;
    recovery.nextActionAt = Date.now() + delayMs;
    recovery.lastProbeStatus = null;
    saveRecovery();
    appendLog('recovery_scheduled', 'Gestaffelte automatische Fortsetzung geplant', {
      sessionId: endEvent.sessionId,
      failureSignature,
      query: endEvent.query || recovery.query || '',
      results: recovery.results,
      recoveryCycle: used + 1,
      recoveryDelayMs: delayMs,
      jitterRatio: options.jitterRatio,
      trigger1101: evidence.has1101,
      trigger1102: evidence.has1102,
      html503RequestCount: evidence.html503RequestCount,
      cfErrorType: evidence.cfErrorType,
      cfErrorOrigin: evidence.cfErrorOrigin,
      retryAfter: evidence.retryAfter,
      rayId: evidence.rayId,
    });
    showWaiting();
  }

  async function probeWorker() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 25000);
    const startedAt = performance.now();
    try {
      const endpoint = new URL(options.probeEndpoint, location.href);
      endpoint.searchParams.set('build', I.buildId);
      endpoint.searchParams.set('probe', String(Date.now()));
      const response = await fetch(endpoint, {
        cache: 'no-store',
        signal: controller.signal,
        headers: {Accept: 'application/json', 'X-GenericParser-Recovery-Probe': '1'},
      });
      const durationMs = Math.round(performance.now() - startedAt);
      const contentType = response.headers.get('content-type') || '';
      const headers = {
        cfErrorType: response.headers.get('cf-error-type') || null,
        cfErrorOrigin: response.headers.get('cf-error-origin') || null,
        retryAfter: response.headers.get('retry-after') || null,
        rayId: response.headers.get('cf-ray') || null,
      };
      let body = null;
      if (contentType.includes('application/json')) {
        try { body = await response.json(); } catch {}
      }
      const identityOk = body && body.version === I.version && body.build_id === I.buildId && body.api_contract === I.apiContract;
      const checksOk = body?.status === 'ready' && body?.search_ready === true && body?.reference_core_loaded === true && Object.values(body?.checks || {}).every(Boolean);
      return {
        ok: response.ok && identityOk && checksOk,
        status: response.status,
        reason: response.ok ? (identityOk && checksOk ? 'Suchpfad bereit' : 'Probe unvollständig oder Identität abweichend') : `HTTP ${response.status}`,
        durationMs,
        body,
        headers,
      };
    } catch (error) {
      return {
        ok: false,
        status: null,
        reason: error?.name === 'AbortError' ? 'Recovery-Probe abgelaufen' : String(error?.message || error),
        durationMs: Math.round(performance.now() - startedAt),
        body: null,
        headers: {},
      };
    } finally {
      clearTimeout(timeout);
    }
  }

  async function waitForResumeButton(timeoutMs = 12000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const button = document.getElementById('resume-button');
      if (button && !button.disabled && !button.classList.contains('hidden')) return button;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    return null;
  }

  async function attemptRecovery() {
    if (!recovery || !['waiting', 'probing'].includes(recovery.status) || probeInFlight) return;
    probeInFlight = true;
    recovery.status = 'probing';
    saveRecovery();
    showWaiting();
    const probeNumber = Number(recovery.probeAttempt || 0) + 1;
    appendLog('recovery_probe_start', 'Recovery-Probe gestartet', {
      sessionId: recovery.failureSessionId,
      recoveryCycle: Number(recovery.autoResumeCount || 0) + 1,
      probeAttempt: probeNumber,
      endpoint: options.probeEndpoint,
    });
    const probe = await probeWorker();
    probeInFlight = false;
    if (!recovery || recovery.status !== 'probing') return;

    recovery.lastProbeStatus = probe.ok ? 'OK' : probe.reason;
    recovery.lastProbeDurationMs = probe.durationMs;
    recovery.lastProbeAt = Date.now();
    if (!probe.ok) {
      recovery.probeAttempt = probeNumber;
      appendLog('recovery_probe_failed', 'Recovery-Probe fehlgeschlagen', {
        sessionId: recovery.failureSessionId,
        recoveryCycle: Number(recovery.autoResumeCount || 0) + 1,
        probeAttempt: probeNumber,
        maxProbeAttempts: options.maxProbeAttempts,
        reason: probe.reason,
        status: probe.status,
        probeDurationMs: probe.durationMs,
        cfErrorType: probe.headers?.cfErrorType || null,
        cfErrorOrigin: probe.headers?.cfErrorOrigin || null,
        retryAfter: probe.headers?.retryAfter || null,
        rayId: probe.headers?.rayId || null,
      });
      if (probeNumber >= options.maxProbeAttempts) {
        requireManual('probe_attempts_exhausted', 'Der vollständige Suchpfad wurde nach mehreren Prüfungen nicht stabil bereit.');
        return;
      }
      const delayMs = probeDelay(probeNumber - 1);
      recovery.nextActionAt = Date.now() + delayMs;
      saveRecovery();
      showWaiting();
      return;
    }

    appendLog('recovery_probe_ready', 'Vollständiger Suchpfad ist bereit', {
      sessionId: recovery.failureSessionId,
      recoveryCycle: Number(recovery.autoResumeCount || 0) + 1,
      probeAttempt: probeNumber,
      probeDurationMs: probe.durationMs,
      workerVersion: probe.body?.version || null,
      workerBuild: probe.body?.build_id || null,
      rayId: probe.body?.ray_id || probe.headers?.rayId || null,
    });

    const button = await waitForResumeButton();
    if (!button) {
      requireManual('resume_control_unavailable', 'Die Recovery-Probe war erfolgreich, aber die Fortsetzen-Schaltfläche wurde nicht bereit.');
      return;
    }

    recovery.status = 'starting_auto';
    recovery.autoResumeCount = Number(recovery.autoResumeCount || 0) + 1;
    recovery.successfulAutoResumes = Number(recovery.successfulAutoResumes || 0) + 1;
    recovery.probeAttempt = probeNumber;
    recovery.nextActionAt = null;
    saveRecovery();
    appendLog('recovery_resume_start', 'Gespeicherte Suche wird automatisch fortgesetzt', {
      sessionId: recovery.failureSessionId,
      failureSignature: recovery.failureSignature,
      autoResumeCount: recovery.autoResumeCount,
      results: recovery.results,
      probeDurationMs: probe.durationMs,
      workerVersion: probe.body?.version || null,
      workerBuild: probe.body?.build_id || null,
    });
    setStatus('Automatische Fortsetzung startet', `Versuch ${recovery.autoResumeCount}/${options.maxAutoResumes} · vollständiger Suchpfad bereit`);
    button.click();
  }

  function processEvent(event, events) {
    if (event.type === 'search_start') {
      resetForNewSearch(event);
      return;
    }

    if (event.type === 'search_resume') {
      if (recovery?.status === 'starting_auto') {
        recovery.status = 'auto_running';
        recovery.currentSessionId = event.sessionId;
        saveRecovery();
        appendLog('recovery_resume_running', 'Automatisch fortgesetzte Suchsession läuft', {
          sessionId: event.sessionId,
          rootSessionId: recovery.rootSessionId,
          autoResumeCount: recovery.autoResumeCount,
        });
        setStatus('Fortgesetzte Suche läuft', `Auto-Resume ${recovery.autoResumeCount}/${options.maxAutoResumes} · ${Number(recovery.results || 0)} Ergebnisse übernommen`);
      }
      return;
    }

    if (event.type !== 'search_end') return;

    if (event.reason === 'retry_exhausted') {
      const evidence = sessionEvidence(events, event.sessionId);
      if (!evidence.recoverable) return;
      scheduleRecovery(event, evidence);
      return;
    }

    if (recovery?.status === 'auto_running' && event.sessionId === recovery.currentSessionId) {
      recovery.status = 'completed';
      recovery.completedSessionId = event.sessionId;
      recovery.completionReason = event.reason || (event.complete ? 'complete' : 'search_end');
      recovery.results = Number(event.results || recovery.results || 0);
      recovery.nextActionAt = null;
      saveRecovery();
      appendLog('recovery_completed', 'Recovery-Kette wurde regulär beendet', {
        sessionId: event.sessionId,
        complete: Boolean(event.complete),
        reason: recovery.completionReason,
        results: recovery.results,
        autoResumeCount: recovery.autoResumeCount,
      });
      setStatus('Recovery abgeschlossen', `${recovery.results} Ergebnisse · ${recovery.autoResumeCount} automatische Fortsetzung(en)`, 'done');
      setTimeout(renderRecoveryPanel, 5000);
    }
  }

  function scanEvents() {
    const events = readEvents();
    const fresh = events
      .filter(event => !processed.has(signatureOf(event)))
      .sort((a, b) => eventEpoch(a) - eventEpoch(b));
    for (const event of fresh) {
      processed.add(signatureOf(event));
      processEvent(event, events);
    }
  }

  function restoreAfterReload(events) {
    if (!recovery) return;
    if (Date.now() - Number(recovery.updatedAt || 0) > MAX_PERSISTED_AGE_MS && ['waiting', 'probing', 'starting_auto'].includes(recovery.status)) {
      requireManual('persisted_recovery_expired', 'Die gespeicherte automatische Recovery ist abgelaufen.');
      return;
    }
    if (['waiting', 'probing'].includes(recovery.status)) {
      showWaiting();
      return;
    }
    if (['running', 'auto_running'].includes(recovery.status)) {
      const sessionId = recovery.currentSessionId || recovery.rootSessionId;
      const terminal = [...events].reverse().find(event => event.type === 'search_end' && event.sessionId === sessionId && event.reason === 'retry_exhausted');
      if (terminal) {
        const evidence = sessionEvidence(events, sessionId);
        if (evidence.recoverable) scheduleRecovery(terminal, evidence);
      }
    }
  }

  function tick() {
    renderRecoveryPanel();
    if (!recovery) return;
    if (['waiting', 'probing'].includes(recovery.status)) {
      showWaiting();
      if (Date.now() >= Number(recovery.nextActionAt || 0)) attemptRecovery();
    }
  }

  function start() {
    if (started) return;
    started = true;
    const events = readEvents();
    events.forEach(event => processed.add(signatureOf(event)));
    restoreAfterReload(events);
    tick();
    setInterval(() => {
      scanEvents();
      tick();
    }, 1000);
  }

  document.addEventListener('click', event => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target || !event.isTrusted) return;
    if (target.closest('#clear-progress')) {
      recovery = null;
      saveRecovery();
      appendLog('recovery_state_cleared', 'Recovery- und Suchstand wurden gelöscht');
      renderRecoveryPanel();
      return;
    }
    if (target.closest('#resume-button') && recovery && ['waiting', 'probing'].includes(recovery.status)) {
      recovery.status = 'cancelled';
      recovery.nextActionAt = null;
      saveRecovery();
      appendLog('recovery_cancelled', 'Automatische Recovery wurde durch manuelles Fortsetzen ersetzt', {
        sessionId: recovery.failureSessionId,
      });
      renderRecoveryPanel();
    }
    if (target.closest('#search-button') && recovery && !['completed', 'cancelled', 'manual_required'].includes(recovery.status)) {
      recovery = null;
      saveRecovery();
      appendLog('recovery_replaced_by_new_search', 'Laufende Recovery wurde durch eine neue Suche ersetzt');
      renderRecoveryPanel();
    }
  }, true);

  window.addEventListener('gp-controller-ready', start, {once: true});
  if (window.GP_CONTROLLER_IDENTITY) start();
})();
