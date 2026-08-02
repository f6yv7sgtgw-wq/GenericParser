(() => {
  'use strict';

  const UI_VERSION = '0.41.1';
  const BUILD_ID = 'gp-0411-20260802-1';
  const API_CONTRACT = 'match-v6.1-page-worker';
  const versionBadge = document.getElementById('worker-version');
  const connection = document.getElementById('connection');
  const searchButton = document.getElementById('search-button');
  const resumeButton = document.getElementById('resume-button');
  const workerText = document.getElementById('worker-state-text');

  let ready = false;
  window.GP_BUILD = Object.freeze({version: UI_VERSION, buildId: BUILD_ID, apiContract: API_CONTRACT});
  window.GP_HANDSHAKE_READY = false;

  function setBlocked(blocked) {
    if (searchButton) searchButton.disabled = blocked;
    if (resumeButton) resumeButton.disabled = blocked;
  }

  function render(title, detail, ok) {
    if (versionBadge) versionBadge.textContent = ok ? UI_VERSION : 'nicht bereit';
    if (connection) {
      connection.classList.toggle('offline', !ok);
      connection.innerHTML = `<span></span> ${ok ? 'Bereit' : 'Deployment prüfen'}`;
    }
    if (workerText) {
      workerText.className = `diagnostic ${ok ? 'done' : 'error'}`;
      workerText.innerHTML = `<span><strong>${title}</strong></span><span>${detail}</span>`;
    }
  }

  async function handshake() {
    ready = false;
    window.GP_HANDSHAKE_READY = false;
    setBlocked(true);
    render('Versionsprüfung läuft', `UI ${UI_VERSION} · Build ${BUILD_ID}`, false);

    try {
      const response = await fetch(`./api/version?build=${encodeURIComponent(BUILD_ID)}`, {
        method: 'GET',
        cache: 'no-store',
        headers: {'Accept': 'application/json', 'X-GenericParser-UI-Version': UI_VERSION, 'X-GenericParser-UI-Build': BUILD_ID}
      });
      const contentType = response.headers.get('content-type') || '';
      const data = contentType.includes('application/json') ? await response.json() : null;
      const headerVersion = response.headers.get('X-GenericParser-Version');
      const headerBuild = response.headers.get('X-GenericParser-Build');
      const version = data?.version || headerVersion;
      const buildId = data?.build_id || headerBuild;
      const contract = data?.api_contract || response.headers.get('X-GenericParser-Contract');
      const consistent = response.ok && data?.search_ready === true && version === UI_VERSION && buildId === BUILD_ID && contract === API_CONTRACT;

      if (!consistent) {
        throw new Error(`UI ${UI_VERSION}/${BUILD_ID} · Worker ${version || 'unbekannt'}/${buildId || 'unbekannt'} · Vertrag ${contract || 'unbekannt'}`);
      }

      ready = true;
      window.GP_HANDSHAKE_READY = true;
      setBlocked(false);
      render('Deployment konsistent', `UI und Worker ${UI_VERSION} · Build ${BUILD_ID}`, true);
      window.gpEventLog?.('deployment_handshake_ok', 'UI und Worker sind konsistent', {uiVersion: UI_VERSION, workerVersion: version, buildId, apiContract: contract});
    } catch (error) {
      setBlocked(true);
      render('Deployment nicht konsistent', String(error?.message || error), false);
      window.gpEventLog?.('deployment_handshake_failed', 'Live-Suche wurde gesperrt', {uiVersion: UI_VERSION, buildId: BUILD_ID, error: String(error?.message || error)});
    }
  }

  document.addEventListener('click', event => {
    const target = event.target instanceof Element ? event.target.closest('#search-button,#resume-button') : null;
    if (!target || ready) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    render('Suche gesperrt', 'UI und Worker müssen zuerst denselben Versions-Handshake bestätigen.', false);
  }, true);

  window.addEventListener('pageshow', event => {
    if (event.persisted) handshake();
  });

  handshake();
})();
