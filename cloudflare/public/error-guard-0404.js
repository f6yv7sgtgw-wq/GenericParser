(() => {
  'use strict';

  const nativeFetch = window.fetch.bind(window);

  window.fetch = async function guardedFetch(input, init) {
    const response = await nativeFetch(input, init);
    const url = typeof input === 'string' ? input : input?.url || '';
    if (!/\/api\/search(?:\?|$)/.test(url)) return response;

    const type = response.headers.get('content-type') || '';
    if (type.includes('application/json')) return response;

    const text = await response.clone().text();
    const is1101 = /Error\s*1101|Worker threw exception/i.test(text);
    if (!is1101) return response;

    const ray = text.match(/Ray ID:\s*([a-f0-9]+)/i)?.[1] || null;
    return new Response(JSON.stringify({
      detail: `Cloudflare Worker-Ausnahme 1101${ray ? ` · Ray-ID ${ray}` : ''}. Kein automatischer Retry.`,
      retryable: false,
      error_type: 'cloudflare_1101',
      ray_id: ray,
      worker: {version: '0.40.4'}
    }), {
      status: 422,
      headers: {'Content-Type': 'application/json; charset=utf-8'}
    });
  };
})();
