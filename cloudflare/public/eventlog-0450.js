(async () => {
  'use strict';
  const I = await (window.GP_BUILD_IDENTITY_READY || Promise.resolve(window.GP_BUILD_IDENTITY));
  if (!I) throw new Error('Shared runtime identity missing');
  const KEY = I.eventLogKey;
  const LEGACY_KEYS = ['generic-parser-eventlog-04465', 'generic-parser-eventlog-04462'];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

  document.title = `Searcherix Log & Diagnose ${I.version}`;
  document.querySelectorAll('[data-version]').forEach(node => { node.textContent = I.version; });
  const footer = document.querySelector('footer span');
  if (footer) footer.textContent = `GenericParser · Build ${I.buildId}`;
  window.GPFavorites?.updateCounts();

  function readKey(key) {
    try {
      const value = JSON.parse(localStorage.getItem(key) || '[]');
      return Array.isArray(value) ? value : [];
    } catch { return []; }
  }

  function rows() {
    const merged = [...readKey(KEY), ...LEGACY_KEYS.flatMap(readKey)];
    const seen = new Set();
    return merged
      .sort((a, b) => Number(a.epoch || Date.parse(a.time) || 0) - Number(b.epoch || Date.parse(b.time) || 0))
      .filter(event => {
        const signature = event.signature || JSON.stringify([event.time, event.type, event.requestId, event.page, event.status, event.message]);
        if (seen.has(signature)) return false;
        seen.add(signature);
        return true;
      });
  }

  function isHtml503(event) {
    return Number(event?.status) === 503 && /text\/html/i.test(String(event?.contentType || ''));
  }

  const titles = {
    source_status: ['Quellenstatus aktualisiert', 'Status der plattformübergreifenden Suche.'],
    before_fetch: ['Suchpaket angefordert', 'Eine Plattformseite wird geladen.'],
    after_fetch: ['Suchpaket empfangen', 'Die Plattformantwort ist eingetroffen.'],
    after_parse: ['Suchpaket verarbeitet', 'Die Antwort wurde geprüft und übernommen.'],
    search_start: ['Suche gestartet', 'Ein neuer Suchlauf wurde gestartet.'],
    search_resume: ['Suche fortgesetzt', 'Ein gespeicherter Suchlauf wurde fortgesetzt.'],
    search_end: ['Suche beendet', 'Der Suchlauf wurde abgeschlossen.'],
    search_stopped: ['Suche pausiert', 'Der gespeicherte Stand kann fortgesetzt werden.'],
    search_error: ['Suchfehler', 'Der Suchlauf wurde mit einem Fehler beendet.'],
    request_error: ['Netzwerkfehler', 'Ein Suchpaket konnte nicht geladen werden.'],
    transport_retry_wait: ['Verbindung wird wiederhergestellt', 'Das unveränderte Suchpaket wird automatisch erneut gesendet.'],
    vinted_catalog: ['Vinted-Katalog durchsucht', 'Vinted-Katalogtreffer wurden geladen.'],
    vinted_detail: ['Vinted-Details angereichert', 'Bilder, Preise und Zustandsdaten wurden ergänzt.'],
    vinted_detail_enrichment: ['Vinted-Details angereichert', 'Detaildaten wurden in die Treffer übernommen.'],
    vinted_scoring: ['Vinted-Treffer bewertet', 'Vinted-Treffer wurden klassifiziert.'],
    vinted_background_ready: ['Vinted-Hintergrundanreicherung bereit', 'Detail-Batches blockieren die Hauptsuche nicht.'],
    vinted_background_batch_start: ['Vinted-Detailbatch gestartet', 'Bis zu drei Detailseiten werden verarbeitet.'],
    vinted_background_batch_end: ['Vinted-Detailbatch abgeschlossen', 'Nachgeladene Daten wurden übernommen.'],
    vinted_background_retry: ['Vinted-Detailbatch wiederholt', 'Ein temporärer Fehler wird erneut versucht.'],
    vinted_background_batch_error: ['Vinted-Detailbatch fehlgeschlagen', 'Die Hauptsuche bleibt verfügbar.'],
    vinted_background_cancelled: ['Vinted-Anreicherung beendet', 'Ausstehende Detail-Batches wurden beendet.'],
    vinted_background_complete: ['Vinted-Anreicherung vollständig', 'Alle geplanten Detail-Batches sind abgeschlossen.'],
    auto_resume_scheduled: ['Fortsetzung geplant', 'Der gespeicherte Suchstand wird vorbereitet.'],
    auto_resume_health_failed: ['Bereitschaftsprüfung fehlgeschlagen', 'Die Suche bleibt manuell verfügbar.'],
    auto_resume_health_ready: ['Worker bereit', 'Die Bereitschaftsprüfung war erfolgreich.'],
    auto_resume_start: ['Fortsetzung gestartet', 'Der gespeicherte Suchstand wird fortgesetzt.'],
    auto_resume_running: ['Fortgesetzte Suche läuft', 'Eine neue Suchsession wurde gestartet.'],
    auto_resume_manual_required: ['Manuelles Fortsetzen erforderlich', 'Die automatische Fortsetzung ist beendet.'],
    module_debug_toggle: ['Debug-Einstellung geändert', 'Der Debugschalter wurde geändert.'],
    module_test_toggle: ['Test-Einstellung geändert', 'Der Testschalter wurde geändert.'],
    module_debug_fetch: ['Moduldiagnose', 'Zeit- und Statusdaten eines API-Aufrufs.'],
    module_debug_report: ['Serverdiagnose', 'Opt-in-Debugdaten des Workers.'],
    module_self_test: ['Modul-Selbsttest', 'Der netzwerkfreie Vertragstest wurde ausgeführt.'],
    module_self_test_error: ['Modul-Selbsttest fehlgeschlagen', 'Der Test konnte nicht ausgeführt werden.'],
    module_profile_validation: ['Suchprofil validiert', 'Das Suchprofil wurde gegen den Kompatibilitätsvertrag geprüft.'],
    module_profile_validation_error: ['Suchprofil ungültig', 'Die Profilvalidierung ist fehlgeschlagen.']
  };

  function eventPresentation(event) {
    if (isHtml503(event)) return {kind: 'problem', title: 'Temporärer Abruffehler (HTTP 503)', message: 'Cloudflare oder die Plattform lieferte HTML statt Suchdaten.'};
    if (event?.type === 'worker_1101') return {kind: 'problem', title: 'Cloudflare-Worker-Ausnahme', message: event.message || 'Worker-Ausnahme vor dem Suchservice.'};
    const type = String(event?.type || '');
    const problem = /error|failed|manual_required|mismatch|blocked|exception/.test(type) || event?.ok === false || Number(event?.status || 0) >= 400;
    if (titles[type]) {
      const [title, fallback] = titles[type];
      return {kind: problem ? 'problem' : 'success', title, message: event.message || fallback};
    }
    return {kind: problem ? 'problem' : 'neutral', title: type || 'Ereignis', message: event?.message || ''};
  }

  function runtimeItem(label, value) {
    return `<div class="runtime-item"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
  }

  async function verify() {
    const box = document.getElementById('version-check');
    try {
      const endpoint = new URL(`./api/version?build=${encodeURIComponent(I.buildId)}`, location.href);
      const response = await fetch(endpoint, {cache: 'no-store', headers: {Accept: 'application/json'}});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const worker = await response.json();
      const supported = Array.isArray(worker.supported_module_contracts) ? worker.supported_module_contracts : [];
      const webContract = worker.web_ui_api_contract || worker.preferred_module_contract || I.webUiApiContract;
      const identityOk = Boolean(worker.version && worker.build_id && supported.includes('generic-parser-module-v2') && webContract === 'generic-parser-module-v2');
      box.innerHTML = [
        `<div class="runtime-heading"><div><p class="eyebrow">Betriebsstatus</p><h2>${identityOk ? 'Alle Systeme bereit' : 'Vertrag prüfen'}</h2></div><span class="runtime-state ${identityOk ? '' : 'degraded'}">${identityOk ? 'Online' : 'Prüfen'}</span></div>`,
        `<p class="runtime-summary">${identityOk ? 'Kleinanzeigen, Vinted und eBay sind verbunden. Ein Diagnosefehler sperrt die Suche nicht mehr.' : 'Die Suche bleibt verfügbar; die angezeigten Vertragsdaten weichen jedoch ab.'}</p>`,
        '<div class="runtime-grid">',
        runtimeItem('Websuche', webContract || 'generic-parser-module-v2'),
        runtimeItem('Kompatibilität', worker.module_contract || worker.api_contract || 'generic-parser-module-v1'),
        runtimeItem('Version', `${worker.version || I.version} · ${worker.build_id || I.buildId}`),
        runtimeItem('Plattformen', 'Kleinanzeigen · Vinted · eBay'),
        runtimeItem('Vinted', 'Service Binding · 3er-Detail-Batches'),
        runtimeItem('eBay', 'Browse API · EBAY_DE'),
        '</div>',
        `<p class="runtime-note">Debug-Logs standardmäßig ${worker.debug_logging?.enabled_by_default ? 'aktiv' : 'aus'} · Produktklassifizierung v1 · passende Treffer zuerst</p>`
      ].join('');
    } catch (error) {
      box.innerHTML = [
        '<div class="runtime-heading"><div><p class="eyebrow">Betriebsstatus</p><h2>Live-Prüfung momentan nicht erreichbar</h2></div><span class="runtime-state checking">Suche offen</span></div>',
        '<p class="runtime-summary">Die Diagnoseverbindung ist fehlgeschlagen. Die Websuche bleibt trotzdem freigeschaltet und meldet einen echten Suchfehler erst beim Suchaufruf.</p>',
        '<div class="runtime-grid">',
        runtimeItem('Websuche', I.webUiApiContract || 'generic-parser-module-v2'),
        runtimeItem('Lokale Release-Identität', `${I.version} · ${I.buildId}`),
        '</div>',
        `<p class="runtime-note">Diagnose: ${esc(error?.message || error)}</p>`
      ].join('');
    }
  }

  function selectedRows(data) {
    const filter = document.getElementById('log-filter')?.value || 'all';
    if (filter === 'problems') return data.filter(event => eventPresentation(event).kind === 'problem');
    if (filter === 'search') return data.filter(event => /search|fetch|parse|resume|transport/.test(String(event.type || '')));
    if (filter === 'sources') return data.filter(event => /source|vinted|ebay|kleinanzeigen/.test(String(event.type || '')));
    return data;
  }

  function render() {
    const all = rows().slice().reverse();
    const data = selectedRows(all);
    const problems = all.filter(event => eventPresentation(event).kind === 'problem');
    const sourceEvents = all.filter(event => event.type === 'source_status');
    document.getElementById('log-summary').innerHTML = [
      `<span>${all.length} Ereignisse</span>`,
      `<span>${problems.length} Probleme</span>`,
      `<span>${sourceEvents.length} Quellenstatus</span>`,
      data.length !== all.length ? `<span>${data.length} angezeigt</span>` : '',
      `<span>Build ${esc(I.buildId)}</span>`
    ].join('');

    document.getElementById('event-log').innerHTML = data.map(event => {
      const presentation = eventPresentation(event);
      const details = Object.entries(event)
        .filter(([key]) => !['time', 'epoch', 'type', 'message', 'signature'].includes(key))
        .map(([key, value]) => `<div class="event-detail"><strong>${esc(key)}</strong>: ${esc(typeof value === 'object' ? JSON.stringify(value) : value)}</div>`)
        .join('');
      const eventTime = event.time ? new Date(event.time).toLocaleString('de-DE') : 'Zeit unbekannt';
      return `<details class="event-card ${presentation.kind}"><summary><span class="event-card-title"><strong>${esc(presentation.title)}</strong><span>${esc(eventTime)}</span></span></summary><div class="event-card-body"><p>${esc(presentation.message)}</p><div class="event-details">${details || `<div class="event-detail">Typ: ${esc(event.type || 'Ereignis')}</div>`}</div></div></details>`;
    }).join('') || '<div class="event-empty">Für diesen Filter sind keine Ereignisse vorhanden.</div>';
  }

  const refresh = () => { render(); verify(); };
  document.getElementById('refresh-log').onclick = refresh;
  document.getElementById('log-filter').onchange = render;
  document.getElementById('clear-log').onclick = () => {
    localStorage.removeItem(KEY);
    LEGACY_KEYS.forEach(key => localStorage.removeItem(key));
    render();
  };
  document.getElementById('copy-log').onclick = async event => {
    const button = event.currentTarget;
    try {
      await navigator.clipboard.writeText(JSON.stringify(rows(), null, 2));
      button.textContent = 'Kopiert';
    } catch {
      button.textContent = 'Kopieren nicht möglich';
    }
    setTimeout(() => { button.textContent = 'Log kopieren'; }, 1600);
  };
  render();
  verify();
  window.addEventListener('gp-identity-status', verify);
  setInterval(render, 3000);
})().catch(error => {
  const box = document.getElementById('version-check');
  if (box) {
    box.innerHTML = `<div class="runtime-heading"><div><p class="eyebrow">Betriebsstatus</p><h2>Log konnte nicht gestartet werden</h2></div><span class="runtime-state degraded">Fehler</span></div><p class="runtime-summary">${String(error?.message || error)}</p>`;
  }
});
