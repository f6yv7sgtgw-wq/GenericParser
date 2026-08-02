(() => {
  'use strict';

  const nativeFetch = window.fetch.bind(window);

  window.fetch = async function diagnosticFetch(input, init) {
    const response = await nativeFetch(input, init);
    const url = typeof input === 'string' ? input : input?.url || '';
    if (!/\/api\/search(?:\?|$)/.test(url)) return response;

    const type = response.headers.get('content-type') || '';
    if (type.includes('application/json')) {
      if (response.ok) return response;
      const data = await response.clone().json().catch(() => null);
      if (!data || typeof data !== 'object') return response;
      const details = [
        data.detail,
        data.phase ? `Phase: ${data.phase}` : null,
        data.query ? `Suchbegriff: ${data.query}` : null,
        data.page != null ? `Seite: ${Number(data.page) + 1}` : null,
        data.source ? `Quelle: ${data.source}` : null,
        data.target_url ? `Ziel: ${data.target_url}` : null,
        data.elapsed_ms != null ? `Laufzeit: ${data.elapsed_ms} ms` : null,
        data.ray_id ? `Ray-ID: ${data.ray_id}` : null,
        data.error_type ? `Fehlertyp: ${data.error_type}` : null
      ].filter(Boolean).join(' · ');
      return new Response(JSON.stringify({...data, detail: details, retryable: false}), {
        status: response.status,
        headers: {'Content-Type': 'application/json; charset=utf-8'}
      });
    }

    const text = await response.clone().text();
    const is1101 = /Error\s*1101|Worker threw exception/i.test(text);
    if (!is1101) return response;
    const ray = text.match(/Ray ID:\s*([a-f0-9]+)/i)?.[1] || null;
    return new Response(JSON.stringify({
      detail: `Cloudflare 1101 vor der ASGI-Diagnose · Phase: runtime_before_asgi${ray ? ` · Ray-ID: ${ray}` : ''}`,
      retryable: false,
      error_type: 'cloudflare_1101',
      phase: 'runtime_before_asgi',
      ray_id: ray,
      worker: {version: '0.40.5', diagnostic_build: true}
    }), {
      status: 422,
      headers: {'Content-Type': 'application/json; charset=utf-8'}
    });
  };

  window.addEventListener('DOMContentLoaded', () => {
    const badge = document.getElementById('worker-version');
    if (badge) badge.textContent = '0.40.5';
  });
})();
