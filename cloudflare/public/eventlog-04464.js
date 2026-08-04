(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Shared build identity missing');
  const KEY = I.eventLogKey;
  const LEGACY_KEYS = ['generic-parser-eventlog-04463', 'generic-parser-eventlog-04462', 'generic-parser-eventlog-04461', 'generic-parser-eventlog-0446'];
  const RECOVERY_KEY = I.autoResume?.recoveryKey || 'generic-parser-auto-resume-04464';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

  function readKey(key, fallback = []) {
    try {
      const value = JSON.parse(localStorage.getItem(key) || 'null');
      return value == null ? fallback : value;
    } catch { return fallback; }
  }

  function rows() {
    const merged = [...readKey(KEY), ...LEGACY_KEYS.flatMap(key => readKey(key))];
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

  const recoveryTitles = {
    recovery_scheduled: ['Recovery geplant', 'Die Suche wird nach gestaffelter Ruhezeit erneut geprüft.'],
    recovery_probe_start: ['Recovery-Probe gestartet', 'Der leichte Worker-Bootstrap wird geprüft.'],
    recovery_probe_failed: ['Recovery-Probe fehlgeschlagen', 'Die nächste Prüfung folgt nach dem gestaffelten Probe-Intervall.'],
    recovery_probe_ready: ['Worker-Bootstrap bereit', 'ASGI und der lazy Search-Service-Einstieg sind bereit; der Suchservice wird erst beim Resume geladen.'],
    recovery_resume_start: ['Automatische Fortsetzung gestartet', 'Der gespeicherte Suchstand wird automatisch geladen.'],
    recovery_resume_running: ['Fortgesetzte Suche läuft', 'Die automatisch gestartete Fortsetzung verarbeitet weitere Arbeitspakete.'],
    recovery_completed: ['Recovery abgeschlossen', 'Die Recovery-Kette wurde regulär beendet.'],
    recovery_manual_required: ['Manuelles Fortsetzen erforderlich', 'Die automatischen Versuche sind beendet; der Suchstand bleibt gespeichert.'],
    recovery_cancelled: ['Recovery abgebrochen', 'Manuelles Fortsetzen hat die Automatik ersetzt.'],
    recovery_state_cleared: ['Recovery-Stand gelöscht', 'Suchstand und Recovery-Zustand wurden zurückgesetzt.'],
    recovery_replaced_by_new_search: ['Recovery ersetzt', 'Eine neue Suche hat die vorherige Recovery-Kette beendet.'],
    recovery_bootstrap_failed: ['Recovery-Script fehlerhaft', 'Das browserseitige Recovery-Script konnte nicht gestartet werden.'],
  };

  function presentation(event) {
    if (isHtml503(event)) return {
      className: 'diagnostic error',
      title: 'Temporärer Abruffehler (HTTP 503)',
      message: 'Cloudflare oder der vorgelagerte Abruf lieferte HTML statt Suchdaten. Der Suchstand bleibt gespeichert.'
    };
    if (event?.type === 'worker_1101') return {
      className: 'diagnostic error',
      title: 'Cloudflare-Worker-Ausnahme 1101',
      message: event.message || 'Worker-Ausnahme vor dem Suchservice.'
    };
    if (recoveryTitles[event?.type]) {
      const [title, fallback] = recoveryTitles[event.type];
      const error = ['recovery_probe_failed','recovery_manual_required','recovery_bootstrap_failed'].includes(event.type);
      return {className:`diagnostic ${error?'error':'done'}`,title,message:event.message||fallback};
    }
    return {className:'diagnostic',title:event?.type||'Ereignis',message:event?.message||''};
  }

  async function verify() {
    const box = document.getElementById('version-check');
    try {
      const endpoint = new URL('./api/version', location.href);
      endpoint.searchParams.set('build', I.buildId);
      const response = await fetch(endpoint, {cache:'no-store', headers:{Accept:'application/json'}});
      const contentType = response.headers.get('content-type') || '';
      if (!response.ok || !contentType.includes('application/json')) {
        box.className = 'diagnostic error';
        box.innerHTML = `<span><strong>Worker vorübergehend nicht erreichbar</strong></span><span>HTTP ${response.status} · Versionsvergleich wird nach Aktualisieren erneut versucht.</span>`;
        return;
      }
      const worker = await response.json();
      const identityOk = worker.version === I.version && worker.build_id === I.buildId && worker.api_contract === I.apiContract;
      const referenceMode = worker.diagnostic_mode === 'reference_optional' || worker.reference_version === '0.44.4';
      const recovery = worker.controller_recovery || {};
      box.className = `diagnostic ${identityOk ? 'done' : 'error'}`;
      box.innerHTML = [
        `<span><strong>${identityOk ? 'Versionen konsistent' : 'Versionsabweichung'}</strong></span>`,
        `<span>Eventlog ${esc(I.version)}/${esc(I.buildId)} · Worker ${esc(worker.version || '?')}/${esc(worker.build_id || '?')}</span>`,
        `<span>API-Vertrag: ${esc(worker.api_contract || '?')}</span>`,
        `<span>Diagnosemodus: ${referenceMode ? 'Referenz 0.44.4' : 'Standard'}</span>`,
        `<span>Bootstrap: ${worker.package_init_executed === false ? 'lazy · Paket-__init__ übersprungen' : 'Standard'}</span>`,
        `<span>Recovery: ${recovery.enabled ? `${recovery.max_auto_resumes} Auto-Resumes · Probe ${esc(recovery.probe_endpoint || '?')} · ${esc(recovery.probe_mode || '?')}` : 'nicht aktiv'}</span>`,
        `<span>Backoff: ${Array.isArray(recovery.backoff_ms) ? recovery.backoff_ms.map(ms=>`${Math.round(ms/1000)} s`).join(' / ') : '–'} · Jitter ${Math.round(Number(recovery.jitter_ratio||0)*100)} %</span>`
      ].join('');
    } catch (error) {
      box.className = 'diagnostic error';
      box.innerHTML = `<span><strong>Worker vorübergehend nicht erreichbar</strong></span><span>${esc(error?.message || error)} · kein belegter Versionskonflikt</span>`;
    }
  }

  function render() {
    const data = rows().slice().reverse();
    const recoveryEvents = data.filter(event => String(event.type || '').startsWith('recovery_'));
    const html503 = data.filter(isHtml503);
    const cf1101 = data.filter(event => event.type === 'worker_1101' || String(event.cfErrorType || '') === '1101');
    const state = readKey(RECOVERY_KEY, null);
    const legacyCount = data.filter(event => ['0.44.6','0.44.6.1','0.44.6.2','0.44.6.3'].includes(event.uiVersion)).length;
    const summary = document.getElementById('log-summary');
    summary.innerHTML = [
      `<span>${data.length} Ereignisse</span>`,
      `<span>${recoveryEvents.length} Recovery-Ereignisse</span>`,
      `<span>${html503.length} HTML-503</span>`,
      `<span>${cf1101.length} Cloudflare-1101</span>`,
      state ? `<span>Recovery-Status: ${esc(state.status || '–')} · Auto-Resumes ${Number(state.autoResumeCount||0)}/${Number(I.autoResume?.maxAutoResumes||2)}</span>` : '<span>Recovery-Status: kein aktiver Stand</span>',
      legacyCount ? `<span>${legacyCount} ältere Referenzereignisse übernommen</span>` : '',
      `<span>${data[0] ? new Date(data[0].time).toLocaleString('de-DE') : 'Noch leer'}</span>`,
      `<span>Build ${esc(I.buildId)}</span>`
    ].join('');

    document.getElementById('event-log').innerHTML = data.map(event => {
      const view = presentation(event);
      const details = Object.entries(event)
        .filter(([key]) => !['time','epoch','type','message','signature'].includes(key))
        .map(([key,value]) => `<span>${esc(key)}: ${esc(typeof value === 'object' ? JSON.stringify(value) : value)}</span>`)
        .join('');
      const time = event.time ? new Date(event.time).toLocaleString('de-DE') : 'Zeit unbekannt';
      return `<div class="${view.className}"><span><strong>${esc(time)}</strong></span><span><strong>${esc(view.title)}</strong></span><span>${esc(view.message)}</span>${details}</div>`;
    }).join('') || '<div class="diagnostic"><span>Noch keine Ereignisse protokolliert.</span></div>';
  }

  document.getElementById('refresh-log').onclick = () => { render(); verify(); };
  document.getElementById('clear-log').onclick = () => {
    localStorage.removeItem(KEY);
    LEGACY_KEYS.forEach(key => localStorage.removeItem(key));
    localStorage.removeItem(RECOVERY_KEY);
    render();
  };
  document.getElementById('copy-log').onclick = async () => {
    await navigator.clipboard.writeText(JSON.stringify({identity:I,recovery:readKey(RECOVERY_KEY,null),events:rows()}, null, 2));
    document.getElementById('copy-log').textContent = 'Kopiert';
  };
  render();
  verify();
  setInterval(render, 3000);
})();
