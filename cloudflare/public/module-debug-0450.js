(() => {
  'use strict';

  const I = window.GP_BUILD_IDENTITY;
  if (!I) return;

  const DEBUG_KEY = I.debug?.storageKey || 'generic-parser-debug-0450';
  const TEST_KEY = I.tests?.storageKey || 'generic-parser-tests-0450';
  let wrapped = false;
  let boundButton = null;

  const active = key => {
    try { return localStorage.getItem(key) === '1'; }
    catch { return false; }
  };

  const store = (key, value) => {
    try { localStorage.setItem(key, value ? '1' : '0'); }
    catch {}
  };

  const log = (type, message, data = {}) => {
    if (typeof window.gpEventLog === 'function') {
      window.gpEventLog(type, message, {moduleVersion: I.version, moduleBuild: I.buildId, ...data});
    }
  };

  const status = (text, kind = '') => {
    const node = document.getElementById('module-debug-status');
    if (!node) return;
    node.className = `diagnostic ${kind}`.trim();
    node.textContent = text;
  };

  const numberOrNull = id => {
    const value = document.getElementById(id)?.value?.trim();
    if (!value) return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const terms = id => String(document.getElementById(id)?.value || '')
    .split(',')
    .map(value => value.trim())
    .filter(Boolean);

  const currentProfile = () => {
    const locationId = numberOrNull('location-id');
    const profile = {
      profile_id: String(document.getElementById('profile-name')?.value || 'manual').trim() || 'manual',
      display_name: String(document.getElementById('profile-name')?.value || 'Manuelle Suche').trim() || 'Manuelle Suche',
      query: String(document.getElementById('query')?.value || '').trim(),
      required_terms: terms('required-terms'),
      excluded_terms: terms('excluded-terms'),
      model_patterns: terms('model-patterns'),
      brands: terms('brands'),
      max_price: numberOrNull('max-price'),
      market_value: numberOrNull('market-value'),
      location_id: locationId,
      accept_bundles: Boolean(document.getElementById('accept-bundles')?.checked),
      accept_incomplete: Boolean(document.getElementById('accept-incomplete')?.checked),
      include_review: Boolean(document.getElementById('include-review')?.checked),
      include_rejected: Boolean(document.getElementById('include-rejected')?.checked),
      sort_by: String(document.getElementById('sort-by')?.value || 'relevance')
    };
    const postalCode = String(document.getElementById('postal-code')?.value || '').trim();
    const radius = numberOrNull('radius-km');
    if (locationId && postalCode) profile.postal_code = postalCode;
    if (locationId && radius !== null) profile.radius_km = radius;
    return profile;
  };

  async function runSelfTest() {
    const testToggle = document.getElementById('module-tests');
    if (!testToggle?.checked) {
      status('Modultests sind deaktiviert.');
      return null;
    }
    status('Netzwerkfreier Modul-Selbsttest läuft …', 'working');
    const started = performance.now();
    try {
      const response = await fetch(I.tests?.endpoint || './api/module/v1/self-test?enabled=true', {
        cache: 'no-store',
        headers: {'Accept': 'application/json', 'X-GenericParser-Tests': '1'}
      });
      const result = await response.json();
      const elapsedMs = Math.round(performance.now() - started);
      log('module_self_test', result.ok ? 'Modul-Selbsttest bestanden' : 'Modul-Selbsttest fehlgeschlagen', {
        ok: Boolean(result.ok),
        status: response.status,
        elapsedMs,
        networkUsed: Boolean(result.network_used),
        checks: result.checks || []
      });
      status(
        result.ok ? `Modultest bestanden · ${result.checks?.length || 0} Prüfungen` : 'Modultest fehlgeschlagen · Eventlog prüfen',
        result.ok ? 'done' : 'error'
      );
      return result;
    } catch (error) {
      log('module_self_test_error', 'Modul-Selbsttest konnte nicht ausgeführt werden', {detail: String(error?.message || error)});
      status(`Modultest nicht verfügbar: ${error?.message || error}`, 'error');
      return null;
    }
  }

  async function validateCurrentProfile() {
    const profile = currentProfile();
    if (!profile.query) return null;
    try {
      const response = await fetch('./api/module/v1/profile/validate', {
        method: 'POST',
        cache: 'no-store',
        headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
        body: JSON.stringify(profile)
      });
      const result = await response.json();
      log('module_profile_validation', result.valid ? 'Modulprofil validiert' : 'Modulprofil ungültig', {
        ok: Boolean(result.valid),
        status: response.status,
        profileId: profile.profile_id,
        emptyFieldsIgnored: result.empty_fields_ignored
      });
      return result;
    } catch (error) {
      log('module_profile_validation_error', 'Modulprofil konnte nicht validiert werden', {detail: String(error?.message || error)});
      return null;
    }
  }

  function wrapFetch() {
    if (wrapped) return;
    wrapped = true;
    const previousFetch = window.fetch.bind(window);
    window.fetch = async function moduleDebugFetch(input, init = {}) {
      const debugEnabled = Boolean(document.getElementById('debug-logs')?.checked);
      const url = typeof input === 'string' ? input : input?.url || '';
      const relevant = /\/api\/(?:search|module\/v1\/)/.test(url);
      const options = {...init};
      if (debugEnabled && relevant) {
        options.headers = new Headers(init.headers || {});
        options.headers.set('X-GenericParser-Debug', '1');
      }
      const started = performance.now();
      try {
        const response = await previousFetch(input, options);
        if (debugEnabled && relevant) {
          const elapsedMs = Math.round(performance.now() - started);
          log('module_debug_fetch', 'Diagnose für API-Aufruf', {
            url,
            status: response.status,
            ok: response.ok,
            elapsedMs
          });
          const contentType = response.headers.get('content-type') || '';
          if (contentType.includes('application/json')) {
            response.clone().json().then(body => {
              if (body?.debug) {
                log('module_debug_report', 'Serverseitiger Debugbericht empfangen', {
                  url,
                  traceId: body.debug.trace_id,
                  elapsedMs: body.debug.elapsed_ms,
                  events: body.debug.events || []
                });
              }
            }).catch(() => {});
          }
        }
        return response;
      } catch (error) {
        if (debugEnabled && relevant) {
          log('module_debug_fetch_error', 'Diagnose-API-Aufruf fehlgeschlagen', {
            url,
            elapsedMs: Math.round(performance.now() - started),
            detail: String(error?.message || error)
          });
        }
        throw error;
      }
    };
  }

  function bindControls() {
    const debugToggle = document.getElementById('debug-logs');
    const testToggle = document.getElementById('module-tests');
    const testButton = document.getElementById('run-module-tests');
    if (debugToggle) {
      debugToggle.checked = active(DEBUG_KEY);
      debugToggle.onchange = () => {
        store(DEBUG_KEY, debugToggle.checked);
        status(debugToggle.checked ? 'Debug-Logs aktiviert.' : 'Debug-Logs deaktiviert.');
        log('module_debug_toggle', debugToggle.checked ? 'Debug-Logs aktiviert' : 'Debug-Logs deaktiviert', {enabled: debugToggle.checked});
      };
    }
    if (testToggle) {
      testToggle.checked = active(TEST_KEY);
      testToggle.onchange = () => {
        store(TEST_KEY, testToggle.checked);
        status(testToggle.checked ? 'Modultests aktiviert.' : 'Modultests deaktiviert.');
        log('module_test_toggle', testToggle.checked ? 'Modultests aktiviert' : 'Modultests deaktiviert', {enabled: testToggle.checked});
      };
    }
    if (testButton) testButton.onclick = event => { event.preventDefault(); void runSelfTest(); };

    const searchButton = document.getElementById('search-button');
    if (searchButton && searchButton !== boundButton) {
      boundButton = searchButton;
      searchButton.addEventListener('click', () => {
        if (testToggle?.checked) {
          void runSelfTest();
          void validateCurrentProfile();
        }
      }, true);
    }
    wrapFetch();
    status(`Debug ${debugToggle?.checked ? 'an' : 'aus'} · Modultests ${testToggle?.checked ? 'an' : 'aus'}`);
  }

  window.addEventListener('gp-controller-ready', bindControls);
  if (window.GP_CONTROLLER_IDENTITY) bindControls();
})();
