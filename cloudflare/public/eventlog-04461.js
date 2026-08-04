(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Shared build identity missing');
  const KEY = I.eventLogKey;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

  function rows() {
    try { return JSON.parse(localStorage.getItem(KEY) || '[]'); }
    catch { return []; }
  }

  function isHtml503(event) {
    return Number(event?.status) === 503 && /text\/html/i.test(String(event?.contentType || ''));
  }

  function eventPresentation(event) {
    if (isHtml503(event)) {
      return {
        className: 'diagnostic error',
        title: 'Temporärer Abruffehler (HTTP 503)',
        message: 'Cloudflare oder der vorgelagerte Abruf lieferte HTML statt Suchdaten. Der gespeicherte Suchstand bleibt erhalten; Retry oder Fortsetzen ist möglich.'
      };
    }
    if (event?.type === 'worker_1101') {
      return {
        className: 'diagnostic error',
        title: 'Cloudflare-Worker-Ausnahme',
        message: event.message || 'Worker-Ausnahme vor dem Suchservice.'
      };
    }
    return {
      className: 'diagnostic',
      title: event?.type || 'Ereignis',
      message: event?.message || ''
    };
  }

  async function verify() {
    const box = document.getElementById('version-check');
    try {
      const endpoint = new URL('./api/version', location.href);
      endpoint.searchParams.set('build', I.buildId);
      const response = await fetch(endpoint, {cache:'no-store', headers:{Accept:'application/json'}});
      const worker = await response.json();
      const identityOk = response.ok && worker.version === I.version && worker.build_id === I.buildId && worker.api_contract === I.apiContract;
      const referenceMode = worker.diagnostic_mode === 'reference_optional' || worker.functional_reference === '0.44.4' || worker.reference_version === '0.44.4';
      const schemaText = worker.coverage_schema || (referenceMode ? 'Referenzmodus – erweitertes Schema optional' : 'nicht verfügbar');
      box.className = `diagnostic ${identityOk ? 'done' : 'error'}`;
      box.innerHTML = [
        `<span><strong>${identityOk ? 'Versionen konsistent' : 'Versionsabweichung'}</strong></span>`,
        `<span>Eventlog ${esc(I.version)}/${esc(I.buildId)} · Worker ${esc(worker.version || '?')}/${esc(worker.build_id || '?')}</span>`,
        `<span>API-Vertrag: ${esc(worker.api_contract || '?')}</span>`,
        `<span>Diagnosemodus: ${referenceMode ? 'Referenz 0.44.4' : 'Standard'} · ${esc(schemaText)}</span>`
      ].join('');
    } catch (error) {
      box.className = 'diagnostic error';
      box.textContent = `Versionsprüfung fehlgeschlagen: ${error?.message || error}`;
    }
  }

  function render() {
    const data = rows().slice().reverse();
    const coverage = data.filter(event => event.type === 'coverage_diagnostics');
    const html503 = data.filter(isHtml503);
    const summary = document.getElementById('log-summary');
    summary.innerHTML = [
      `<span>${data.length} Ereignisse</span>`,
      `<span>Referenzdiagnose${coverage.length ? ` · ${coverage.length} Zusatzblöcke` : ''}</span>`,
      `<span>${html503.length} temporäre HTML-503-Antworten</span>`,
      `<span>${data[0] ? new Date(data[0].time).toLocaleString('de-DE') : 'Noch leer'}</span>`,
      `<span>Build ${esc(I.buildId)}</span>`
    ].join('');

    document.getElementById('event-log').innerHTML = data.map(event => {
      const presentation = eventPresentation(event);
      const details = Object.entries(event)
        .filter(([key]) => !['time','epoch','type','message','signature'].includes(key))
        .map(([key,value]) => `<span>${esc(key)}: ${esc(typeof value === 'object' ? JSON.stringify(value) : value)}</span>`)
        .join('');
      return `<div class="${presentation.className}"><span><strong>${esc(new Date(event.time).toLocaleString('de-DE'))}</strong></span><span><strong>${esc(presentation.title)}</strong></span><span>${esc(presentation.message)}</span>${details}</div>`;
    }).join('') || '<div class="diagnostic"><span>Noch keine Ereignisse protokolliert.</span></div>';
  }

  document.getElementById('refresh-log').onclick = () => { render(); verify(); };
  document.getElementById('clear-log').onclick = () => { localStorage.removeItem(KEY); render(); };
  document.getElementById('copy-log').onclick = async () => {
    await navigator.clipboard.writeText(JSON.stringify(rows(), null, 2));
    document.getElementById('copy-log').textContent = 'Kopiert';
  };
  render();
  verify();
  setInterval(render, 3000);
})();
