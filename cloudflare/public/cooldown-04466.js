(() => {
  'use strict';

  const I = window.GP_BUILD_IDENTITY;
  const originalCountdown = window.countdown;

  // Fail open: the stable 0.44.6.5 search remains usable even when this
  // optional experiment cannot initialize.
  if (!I || typeof originalCountdown !== 'function') {
    console.warn('GenericParser cooldown test inactive: reference countdown unavailable');
    return;
  }

  const STEP = Math.max(1, Number(I.testCooldown?.threshold || 120));
  const DURATION_MS = Math.max(0, Number(I.testCooldown?.durationMs || 90000));
  const STATE_KEY = 'generic-parser-cooldown-04466-b3';
  const PROFILE_FIELDS = [
    'query', 'required-terms', 'excluded-terms', 'model-patterns', 'brands',
    'max-price', 'market-value', 'postal-code', 'location-id', 'radius-km'
  ];

  const readState = () => {
    try {
      const value = JSON.parse(localStorage.getItem(STATE_KEY) || 'null');
      return value && typeof value === 'object' ? value : null;
    } catch {
      return null;
    }
  };

  const writeState = value => {
    try { localStorage.setItem(STATE_KEY, JSON.stringify(value)); }
    catch { /* Search remains functional without persisted test state. */ }
  };

  const profileSignature = () => JSON.stringify(PROFILE_FIELDS.map(id => {
    const field = document.getElementById(id);
    return [id, String(field?.value || '')];
  }));

  const log = (type, message, data = {}) => {
    if (typeof window.gpEventLog === 'function') {
      window.gpEventLog(type, message, {
        ...data,
        cooldownBuild: I.buildId,
        cooldownMode: 'repeated-multiples-fail-open'
      });
    }
  };

  const normalizeState = loaded => {
    const signature = profileSignature();
    const count = Math.max(0, Number(loaded || 0));
    let state = readState();

    // A changed profile or a lower result count identifies a new search.
    if (!state || state.signature !== signature || count < Number(state.lastObserved || 0)) {
      state = {
        signature,
        nextThreshold: STEP,
        lastObserved: count,
        completedThresholds: [],
        pendingThreshold: null,
        pendingUntil: 0
      };
    }

    state.lastObserved = count;
    if (!Array.isArray(state.completedThresholds)) state.completedThresholds = [];
    if (!Number.isFinite(Number(state.nextThreshold)) || Number(state.nextThreshold) < STEP) {
      state.nextThreshold = STEP;
    }
    return state;
  };

  window.countdown = async function cooldownAwareCountdown(ms, page, loaded, label = 'Nächste Seite') {
    // Retry waits and all other countdowns remain exactly as in 0.44.6.5.
    if (label !== 'Nächste Seite') {
      return originalCountdown(ms, page, loaded, label);
    }

    const count = Math.max(0, Number(loaded || 0));
    let state = normalizeState(count);
    let threshold = null;
    let waitMs = Number(ms || 0);
    const now = Date.now();

    // Resume an interrupted cooldown after reload for the remaining time.
    if (state.pendingThreshold && count >= Number(state.pendingThreshold)) {
      threshold = Number(state.pendingThreshold);
      waitMs = Math.max(0, Number(state.pendingUntil || 0) - now);
      if (waitMs <= 0) {
        if (!state.completedThresholds.includes(threshold)) state.completedThresholds.push(threshold);
        state.pendingThreshold = null;
        state.pendingUntil = 0;
        writeState(state);
        return originalCountdown(ms, page, loaded, label);
      }
    } else if (count >= Number(state.nextThreshold)) {
      // For an already saved search, use the highest crossed multiple.
      threshold = Math.max(Number(state.nextThreshold), Math.floor(count / STEP) * STEP);
      state.nextThreshold = threshold + STEP;
      state.pendingThreshold = threshold;
      state.pendingUntil = now + DURATION_MS;
      writeState(state);
      waitMs = DURATION_MS;

      log('cooldown_threshold_reached', 'Schwelle für wiederholte Testpause erreicht', {
        threshold,
        uniqueResults: count,
        nextThreshold: state.nextThreshold,
        durationMs: DURATION_MS
      });
      log('cooldown_start', '90-Sekunden-Testpause gestartet', {
        threshold,
        uniqueResults: count,
        nextThreshold: state.nextThreshold,
        durationMs: DURATION_MS
      });
    } else {
      writeState(state);
      return originalCountdown(ms, page, loaded, label);
    }

    await originalCountdown(waitMs, page, loaded, `Testpause nach ${threshold} Treffern`);

    state = readState() || state;
    if (typeof stopRequested !== 'undefined' && stopRequested) {
      log('cooldown_cancelled', 'Testpause durch Suchstopp beendet', {
        threshold,
        uniqueResults: count,
        remainingMs: Math.max(0, Number(state.pendingUntil || 0) - Date.now())
      });
      return;
    }

    if (!state.completedThresholds.includes(threshold)) state.completedThresholds.push(threshold);
    state.pendingThreshold = null;
    state.pendingUntil = 0;
    state.lastObserved = count;
    writeState(state);

    log('cooldown_resume', 'Suche nach 90-Sekunden-Testpause fortgesetzt', {
      threshold,
      uniqueResults: count,
      nextThreshold: state.nextThreshold,
      durationMs: DURATION_MS
    });
  };

  document.getElementById('clear-progress')?.addEventListener('click', () => {
    try { localStorage.removeItem(STATE_KEY); } catch {}
  });

  window.GP_COOLDOWN_IDENTITY = {
    buildId: I.buildId,
    reference: '0.44.6.5',
    step: STEP,
    durationMs: DURATION_MS,
    mode: 'repeated-multiples-fail-open'
  };
})();
