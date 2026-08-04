(() => {
  'use strict';

  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');

  const options = {
    quietPeriodMs: Number(I.autoResume?.quietPeriodMs || 90000),
    healthIntervalMs: Number(I.autoResume?.healthIntervalMs || 15000),
    maxHealthChecks: Number(I.autoResume?.maxHealthChecks || 4),
    maxAutoResumes: Number(I.autoResume?.maxAutoResumes || 1),
  };
  const RECOVERY_KEY = 'generic-parser-auto-resume-04462';
  const MAX_PERSISTED_AGE_MS = 30 * 60 * 1000;
  let recovery = loadRecovery();
  let lastEpoch = 0;
  let healthInFlight = false;
  let started = false;

  function loadRecovery() {
    try {
      const value = JSON.parse(localStorage.getItem(RECOVERY_KEY) || 'null');
      return value && typeof value === 'object' ? value : null;
    } catch { return null; }
  }

  function saveRecovery() {
    if (!recovery) {
      localStorage.removeItem(RECOVERY_KEY);
      return;
    }
    recovery.updatedAt = Date.now();
    localStorage.setItem(RECOVERY_KEY, JSON.stringify(recovery));
  }

  function readEvents() {
    try {
      const value = JSON.parse(localStorage.getItem(I.eventLogKey) || '[]');
      return Array.isArray(value) ? value : [];
    } catch { return []; }
  }

  function appendLog(type, message, data = {}) {
    if (typeof window.gpEventLog === 'function') {
      window.gpEventLog(type, message, {autoResumeVersion: I.version, ...data});
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
        autoResumeVersion: I.version,
        ...data,
        signature: JSON.stringify([type, data.sessionId, data.failureSignature, epoch]),
      });
      localStorage.setItem(I.eventLogKey, JSON.stringify(rows.slice(-400)));
    } catch {}
  }

  function eventEpoch(event) {
    return Number(event?.epoch || Date.parse(event?.time) || 0);
  }

  function sessionEvidence(events, sessionId) {
    const session = events.filter(event => event.sessionId === sessionId);
    const has1101 = session.some(event => event.type === 'worker_1101' || event.errorType === 'cloudflare_1101');
    const html503Requests = new Set(
      session
        .filter(event => Number(event.status) === 503 && /text\/html/i.test(String(event.contentType || '')))
        .map(event => event.requestId || `${event.page || 0}:${event.time || ''}`)
    );
    return {
      has1101,
      html503RequestCount: html503Requests.size,
      recoverable: has1101 || html503Requests.size >= 2,
    };
  }

  function stateElement() {
    return document.getElementById('worker-state-text');
  }

  function messageElement() {
    return document.getElementById('message');
  }

  function formatSeconds(milliseconds) {
    return `${Math.max(0, Math.ceil(milliseconds / 1000))} s`;
  }

  function showWaiting() {
    if (!recovery || !['waiting', 'probing'].includes(recovery.status)) return;
    const remaining = Math.max(0, Number(recovery.nextActionAt || 0) - Date.now());
    const title = recovery.status === 'probing' ? 'Worker-Neustart wird geprüft' : 'Automatische Fortsetzung vorbereitet';
    const detail = recovery.status === 'probing'
      ? `Bereitschaftsprüfung ${Number(recovery.healthChecks || 0) + 1}/${options.maxHealthChecks} in ${formatSeconds(remaining)}`
      : `Fortsetzung in ${formatSeconds(remaining)} · ${Number(recovery.results || 0)} Ergebnisse gespeichert`;
    const state = stateElement();
    if (state) {
      state.className = 'compact-status working';
      state.innerHTML = `<strong>${title}</strong><span>${detail}</span>`;
    }
    const message = messageElement();
    if (message) {
      message.className = 'message';
      message.textContent = `Der Suchstand bleibt gespeichert. Nach einer Ruhezeit wird der Worker geprüft und die Suche einmal automatisch fortgesetzt.`;
    }
  }

  function requireManual(reason, detail) {
    if (!recovery) recovery = {};
    recovery.status = 'manual_required';
    recovery.manualReason = reason;
    saveRecovery();
    appendLog('auto_resume_manual_required', 'Automatische Fortsetzung beendet; manuelles Fortsetzen erforderlich', {
      sessionId: recovery.failureSessionId,
      reason,
      detail,
      autoResumeCount: Number(recovery.autoResumeCount || 0),
      results: Number(recovery.results || 0),
    });
    const state = stateElement();
    if (state) {
      state.className = 'compact-status error';
      state.innerHTML = `<strong>Fortsetzung bereit</strong><span>${detail} · Suchstand gespeichert</span>`;
    }
    const message = messageElement();
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
      healthChecks: 0,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    saveRecovery();
  }

  function scheduleRecovery(endEvent, evidence) {
    if (!recovery) {
      recovery = {
        rootSessionId: endEvent.sessionId,
        query: endEvent.query || '',
        autoResumeCount: 0,
        createdAt: Date.now(),
      };
    }
    if (Number(recovery.autoResumeCount || 0) >= options.maxAutoResumes) {
      requireManual('auto_resume_limit_reached', 'Der einmalige automatische Fortsetzungsversuch wurde bereits verwendet.');
      return;
    }
    const signature = `${endEvent.sessionId || 'session'}:${endEvent.results || 0}:${endEvent.reason || 'retry_exhausted'}`;
    if (recovery.failureSignature === signature && ['waiting', 'probing', 'starting_auto'].includes(recovery.status)) return;
    recovery.status = 'waiting';
    recovery.failureSessionId = endEvent.sessionId;
    recovery.failureSignature = signature;
    recovery.results = Number(endEvent.results || 0);
    recovery.pages = Number(endEvent.pages || 0);
    recovery.requests = Number(endEvent.requests || 0);
    recovery.healthChecks = 0;
    recovery.nextActionAt = Date.now() + options.quietPeriodMs;
    recovery.evidence = evidence;
    saveRecovery();
    appendLog('auto_resume_scheduled', 'Einmalige automatische Fortsetzung geplant', {
      sessionId: endEvent.sessionId,
      failureSignature: signature,
      query: endEvent.query || recovery.query || '',
      results: recovery.results,
      quietPeriodMs: options.quietPeriodMs,
      trigger1101: evidence.has1101,
      html503RequestCount: evidence.html503RequestCount,
    });
    showWaiting();
  }

  async function probeWorker() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const endpoint = new URL('./api/version', location.href);
      endpoint.searchParams.set('build', I.buildId);
      endpoint.searchParams.set('recovery_probe', String(Date.now()));
      const response = await fetch(endpoint, {
        cache: 'no-store',
        signal: controller.signal,
        headers: {Accept: 'application/json', 'X-GenericParser-Recovery-Probe': '1'},
      });
      const contentType = response.headers.get('content-type') || '';
      if (!response.ok || !contentType.includes('application/json')) {
        return {ok: false, reason: `HTTP ${response.status} ${contentType || 'ohne Content-Type'}`};
      }
      const worker = await response.json();
      const identityOk = worker.version === I.version && worker.build_id === I.buildId && worker.api_contract === I.apiContract;
      return {
        ok: identityOk && worker.search_ready !== false,
        reason: identityOk ? 'Worker bereit' : 'Versions- oder Buildabweichung',
        worker,
      };
    } catch (error) {
      return {ok: false, reason: error?.name === 'AbortError' ? 'Bereitschaftsprüfung abgelaufen' : String(error?.message || error)};
    } finally {
      clearTimeout(timeout);
    }
  }

  async function waitForResumeButton(timeoutMs = 10000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const button = document.getElementById('resume-button');
      if (button && !button.disabled && !button.classList.contains('hidden')) return button;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    return null;
  }

  async function attemptRecovery() {
    if (!recovery || !['waiting', 'probing'].includes(recovery.status) || healthInFlight) return;
    healthInFlight = true;
    recovery.status = 'probing';
    saveRecovery();
    showWaiting();
    const probe = await probeWorker();
    healthInFlight = false;

    if (!recovery || recovery.status !== 'probing') return;
    if (!probe.ok) {
      recovery.healthChecks = Number(recovery.healthChecks || 0) + 1;
      appendLog('auto_resume_health_failed', 'Worker noch nicht für automatische Fortsetzung bereit', {
        sessionId: recovery.failureSessionId,
        healthCheck: recovery.healthChecks,
        maxHealthChecks: options.maxHealthChecks,
        reason: probe.reason,
      });
      if (recovery.healthChecks >= options.maxHealthChecks) {
        requireManual('health_checks_exhausted', 'Der Worker wurde nach mehreren Prüfungen nicht stabil bereit.');
        return;
      }
      recovery.nextActionAt = Date.now() + options.healthIntervalMs;
      saveRecovery();
      showWaiting();
      return;
    }

    const button = await waitForResumeButton();
    if (!button) {
      requireManual('resume_control_unavailable', 'Die gespeicherte Suche ist vorhanden, aber die Fortsetzen-Schaltfläche wurde nicht bereit.');
      return;
    }

    recovery.status = 'starting_auto';
    recovery.autoResumeCount = Number(recovery.autoResumeCount || 0) + 1;
    recovery.healthWorkerVersion = probe.worker?.version || null;
    recovery.healthWorkerBuild = probe.worker?.build_id || null;
    saveRecovery();
    appendLog('auto_resume_start', 'Gespeicherte Suche wird automatisch einmal fortgesetzt', {
      sessionId: recovery.failureSessionId,
      failureSignature: recovery.failureSignature,
      autoResumeCount: recovery.autoResumeCount,
      results: recovery.results,
      workerVersion: recovery.healthWorkerVersion,
      workerBuild: recovery.healthWorkerBuild,
    });
    const state = stateElement();
    if (state) {
      state.className = 'compact-status working';
      state.innerHTML = '<strong>Automatische Fortsetzung startet</strong><span>Worker ist bereit · gespeicherter Stand wird geladen</span>';
    }
    button.click();
  }

  function processEvent(event, allEvents) {
    if (event.type === 'search_start') {
      resetForNewSearch(event);
      return;
    }
    if (event.type === 'search_resume') {
      if (recovery?.status === 'starting_auto') {
        recovery.status = 'auto_running';
        recovery.currentSessionId = event.sessionId;
        saveRecovery();
        appendLog('auto_resume_running', 'Automatisch fortgesetzte Suchsession läuft', {
          sessionId: event.sessionId,
          rootSessionId: recovery.rootSessionId,
          autoResumeCount: recovery.autoResumeCount,
        });
      }
      return;
    }
    if (event.type !== 'search_end') return;

    if (event.reason === 'retry_exhausted') {
      const evidence = sessionEvidence(allEvents, event.sessionId);
      if (!evidence.recoverable) return;
      if (recovery?.status === 'auto_running' || Number(recovery?.autoResumeCount || 0) >= options.maxAutoResumes) {
        requireManual('auto_resumed_session_failed', 'Auch die einmal automatisch fortgesetzte Session wurde unterbrochen.');
        return;
      }
      scheduleRecovery(event, evidence);
      return;
    }

    if (recovery?.status === 'auto_running') {
      recovery.status = 'completed';
      recovery.completedSessionId = event.sessionId;
      recovery.completionReason = event.reason || (event.complete ? 'complete' : 'search_end');
      saveRecovery();
      appendLog('auto_resume_completed', 'Automatisch fortgesetzte Session wurde beendet', {
        sessionId: event.sessionId,
        complete: Boolean(event.complete),
        reason: recovery.completionReason,
        results: Number(event.results || 0),
      });
    }
  }

  function scanEvents() {
    const events = readEvents();
    const fresh = events
      .filter(event => eventEpoch(event) > lastEpoch)
      .sort((a, b) => eventEpoch(a) - eventEpoch(b));
    for (const event of fresh) {
      lastEpoch = Math.max(lastEpoch, eventEpoch(event));
      processEvent(event, events);
    }
  }

  function tick() {
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
    lastEpoch = events.reduce((maximum, event) => Math.max(maximum, eventEpoch(event)), 0);
    if (recovery && Date.now() - Number(recovery.updatedAt || 0) > MAX_PERSISTED_AGE_MS && ['waiting', 'probing'].includes(recovery.status)) {
      requireManual('persisted_recovery_expired', 'Die automatische Fortsetzung ist abgelaufen.');
    }
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
      appendLog('auto_resume_state_cleared', 'Automatischer Fortsetzungsstand zusammen mit Suchstand gelöscht');
      return;
    }
    if (target.closest('#resume-button') && recovery && ['waiting', 'probing'].includes(recovery.status)) {
      recovery.status = 'manual_override';
      saveRecovery();
      appendLog('auto_resume_cancelled', 'Automatische Fortsetzung durch manuelles Fortsetzen ersetzt', {
        sessionId: recovery.failureSessionId,
      });
    }
  }, true);

  window.addEventListener('gp-controller-ready', start, {once: true});
  if (window.GP_CONTROLLER_IDENTITY) start();
})();
