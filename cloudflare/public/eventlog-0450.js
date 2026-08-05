(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Shared build identity missing');
  const KEY = I.eventLogKey;
  const LEGACY_KEYS = ['generic-parser-eventlog-04465','generic-parser-eventlog-04462'];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

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
      .sort((a,b) => Number(a.epoch || Date.parse(a.time) || 0) - Number(b.epoch || Date.parse(b.time) || 0))
      .filter(event => {
        const signature = event.signature || JSON.stringify([event.time,event.type,event.requestId,event.page,event.status,event.message]);
        if (seen.has(signature)) return false;
        seen.add(signature);
        return true;
      });
  }

  function isHtml503(event) {
    return Number(event?.status) === 503 && /text\/html/i.test(String(event?.contentType || ''));
  }

  const titles = {
    auto_resume_scheduled: ['Automatische Fortsetzung geplant', 'Stabile Recovery aus 0.44.6.5.'],
    auto_resume_health_failed: ['Worker noch nicht bereit', 'Bereitschaftsprüfung fehlgeschlagen.'],
    auto_resume_health_ready: ['Worker bereit', 'Bereitschaftsprüfung war erfolgreich.'],
    auto_resume_start: ['Automatische Fortsetzung gestartet', 'Gespeicherter Suchstand wird fortgesetzt.'],
    auto_resume_running: ['Fortgesetzte Session läuft', 'Neue Suchsession wurde gestartet.'],
    auto_resume_manual_required: ['Manuelles Fortsetzen erforderlich', 'Der einmalige automatische Versuch ist beendet.'],
    module_debug_toggle: ['Debug-Logs geändert', 'Der Debugschalter wurde geändert.'],
    module_test_toggle: ['Modultests geändert', 'Der Testschalter wurde geändert.'],
    module_debug_fetch: ['Modul-Debug', 'Zeit- und Statusdaten eines API-Aufrufs.'],
    module_debug_report: ['Server-Debugbericht', 'Opt-in-Debugdaten des Workers.'],
    module_self_test: ['Modul-Selbsttest', 'Netzwerkfreier Vertrags- und Adaptertest.'],
    module_self_test_error: ['Modul-Selbsttest fehlgeschlagen', 'Selbsttest konnte nicht ausgeführt werden.'],
    module_profile_validation: ['Modulprofil validiert', 'Aktuelles UI-Profil wurde gegen module v1 geprüft.'],
    module_profile_validation_error: ['Modulprofil ungültig', 'Profilvalidierung ist fehlgeschlagen.']
  };

  function eventPresentation(event) {
    if (isHtml503(event)) {
      return {className:'diagnostic error', title:'Temporärer Abruffehler (HTTP 503)', message:'Cloudflare oder der vorgelagerte Abruf lieferte HTML statt Suchdaten.'};
    }
    if (event?.type === 'worker_1101') {
      return {className:'diagnostic error', title:'Cloudflare-Worker-Ausnahme', message:event.message || 'Worker-Ausnahme vor dem Suchservice.'};
    }
    if (titles[event?.type]) {
      const [title, fallback] = titles[event.type];
      const error = /error|manual_required/.test(String(event.type)) || event.ok === false;
      return {className:`diagnostic ${error ? 'error' : 'done'}`, title, message:event.message || fallback};
    }
    return {className:'diagnostic', title:event?.type || 'Ereignis', message:event?.message || ''};
  }

  async function verify() {
    const box = document.getElementById('version-check');
    try {
      const endpoint = new URL('./api/version', location.href);
      endpoint.searchParams.set('build', I.buildId);
      const response = await fetch(endpoint, {cache:'no-store', headers:{Accept:'application/json'}});
      const worker = await response.json();
      const identityOk = response.ok && worker.version === I.version && worker.build_id === I.buildId && worker.api_contract === I.apiContract;
      box.className = `diagnostic ${identityOk ? 'done' : 'error'}`;
      box.innerHTML = [
        `<span><strong>${identityOk ? 'Versionen konsistent' : 'Versionsabweichung'}</strong></span>`,
        `<span>Eventlog ${esc(I.version)}/${esc(I.buildId)} · Worker ${esc(worker.version || '?')}/${esc(worker.build_id || '?')}</span>`,
        `<span>Modulvertrag: ${esc(worker.module_contract || worker.api_contract || '?')}</span>`,
        `<span>Suchreferenz: ${esc(worker.operational_reference || '0.44.6.5')} · Kern ${esc(worker.functional_reference || worker.reference_version || '0.44.4')}</span>`,
        `<span>Debug-Logs: standardmäßig ${worker.debug_logging?.enabled_by_default ? 'an' : 'aus'}</span>`,
        `<span>Modultests: standardmäßig ${worker.contract_tests?.enabled_by_default ? 'an' : 'aus'} · Netzwerk ${worker.contract_tests?.network_used ? 'ja' : 'nein'}</span>`
      ].join('');
    } catch (error) {
      box.className = 'diagnostic error';
      box.textContent = `Versionsprüfung fehlgeschlagen: ${error?.message || error}`;
    }
  }

  function render() {
    const data = rows().slice().reverse();
    const html503 = data.filter(isHtml503);
    const auto = data.filter(event => String(event.type || '').startsWith('auto_resume_'));
    const debug = data.filter(event => String(event.type || '').startsWith('module_debug_'));
    const tests = data.filter(event => String(event.type || '').startsWith('module_self_test'));
    const profiles = data.filter(event => String(event.type || '').startsWith('module_profile_'));
    const legacyCount = data.filter(event => event.uiVersion && event.uiVersion !== I.version).length;
    document.getElementById('log-summary').innerHTML = [
      `<span>${data.length} Ereignisse</span>`,
      `<span>${debug.length} Debug-Ereignisse</span>`,
      `<span>${tests.length} Modultests</span>`,
      `<span>${profiles.length} Profilprüfungen</span>`,
      `<span>${html503.length} HTML-503-Antworten</span>`,
      `<span>${auto.length} Recovery-Ereignisse</span>`,
      legacyCount ? `<span>${legacyCount} Referenzereignisse übernommen</span>` : '',
      `<span>Build ${esc(I.buildId)}</span>`
    ].join('');

    document.getElementById('event-log').innerHTML = data.map(event => {
      const presentation = eventPresentation(event);
      const details = Object.entries(event)
        .filter(([key]) => !['time','epoch','type','message','signature'].includes(key))
        .map(([key,value]) => `<span>${esc(key)}: ${esc(typeof value === 'object' ? JSON.stringify(value) : value)}</span>`)
        .join('');
      const eventTime = event.time ? new Date(event.time).toLocaleString('de-DE') : 'Zeit unbekannt';
      return `<div class="${presentation.className}"><span><strong>${esc(eventTime)}</strong></span><span><strong>${esc(presentation.title)}</strong></span><span>${esc(presentation.message)}</span>${details}</div>`;
    }).join('') || '<div class="diagnostic"><span>Noch keine Ereignisse protokolliert.</span></div>';
  }

  document.getElementById('refresh-log').onclick = () => { render(); verify(); };
  document.getElementById('clear-log').onclick = () => {
    localStorage.removeItem(KEY);
    LEGACY_KEYS.forEach(key => localStorage.removeItem(key));
    localStorage.removeItem('generic-parser-auto-resume-0450');
    render();
  };
  document.getElementById('copy-log').onclick = async () => {
    await navigator.clipboard.writeText(JSON.stringify(rows(), null, 2));
    document.getElementById('copy-log').textContent = 'Kopiert';
  };
  render();
  verify();
  setInterval(render, 3000);
})();
