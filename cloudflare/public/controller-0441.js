(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');
  window.GP_HANDSHAKE_READY = true;

  const sourceUrl = new URL('./controller-0411.js?v=0.441-stable-source', location.href);
  fetch(sourceUrl, {cache: 'no-store'})
    .then(response => {
      if (!response.ok) throw new Error(`Controller source HTTP ${response.status}`);
      return response.text();
    })
    .then(source => {
      const replacements = [
        ["const VERSION = '0.41.1';", `const VERSION = '${I.version}';`],
        ["const BUILD_ID = 'gp-0411-20260802-1';", `const BUILD_ID = '${I.buildId}';`],
        ["const API_CONTRACT = 'match-v6.1-page-worker';", `const API_CONTRACT = '${I.apiContract}';`],
        ["const LOG_KEY = 'generic-parser-eventlog-0411';", `const LOG_KEY = '${I.eventLogKey}';`]
      ];
      for (const [from, to] of replacements) {
        if (!source.includes(from)) throw new Error(`Controller constant missing: ${from}`);
        source = source.replace(from, to);
      }

      const cardPattern = /function card\(x\)\{[\s\S]*?\}function sorted/;
      if (!cardPattern.test(source)) throw new Error('Stable card renderer boundary not found');
      const optimizedCard = `function card(x){
        const m=matchOf(x),i=x&&typeof x.result_info==='object'&&x.result_info?x.result_info:{};
        const tone=String(i.fit_tone||'review');
        const fitLabel=String(i.fit_label||i.fit||'Prüfen');
        const details=String(i.compact_details||i.display_text||m.reason||'Produkt');
        const place=[x.postal_code,x.place].filter(Boolean).join(' ');
        const shipping=x.shipping_available===true?'Versand möglich':x.shipping_available===false?'Nur Abholung':'';
        const meta=[place,shipping].filter(Boolean).join(' · ');
        const price=x.price!=null?esc(x.price)+' €':esc(x.price_raw||'Preis offen');
        return '<article class="listing optimized-listing tone-'+esc(tone)+'">'
          +'<div class="listing-image">'+(x.image_url?'<img src="'+esc(x.image_url)+'" loading="lazy">':'KEIN BILD')+'</div>'
          +'<div class="listing-body">'
          +'<div class="result-badge tone-'+esc(tone)+'">'+esc(fitLabel)+'</div>'
          +'<h3><a href="'+esc(x.url)+'" target="_blank" rel="noopener">'+esc(x.title)+'</a></h3>'
          +'<div class="price optimized-price">'+price+'</div>'
          +'<div class="semantic-details">'+esc(details)+'</div>'
          +(meta?'<div class="meta">'+esc(meta)+'</div>':'')
          +'</div></article>';
      }
      function sorted`;
      source = source.replace(cardPattern, optimizedCard);

      Function(`${source}\n//# sourceURL=controller-0441-runtime.js`)();

      const button = document.getElementById('search-button');
      if (button) { button.disabled = false; button.textContent = 'Live-Suche starten'; }
      const connection = document.getElementById('connection');
      if (connection) { connection.classList.remove('offline'); connection.innerHTML = '<span></span> Bereit'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className = 'compact-status done'; state.innerHTML = '<strong>Bereit</strong><span>Stabiler 0.43.6.3-Suchfluss mit optimierten Karten</span>'; }
      const toggle = document.getElementById('technical-toggle');
      const technical = document.getElementById('technical-content');
      if (toggle && technical) {
        toggle.onclick = () => {
          const open = technical.classList.toggle('open');
          toggle.setAttribute('aria-expanded', String(open));
          toggle.textContent = open ? 'Technische Details schließen' : 'Technische Details anzeigen';
        };
      }
      window.GP_CONTROLLER_IDENTITY = {version:I.version,buildId:I.buildId,apiContract:I.apiContract,module:'controller-0441.js',stableBase:'0.43.6.3'};
      window.dispatchEvent(new CustomEvent('gp-controller-ready',{detail:window.GP_CONTROLLER_IDENTITY}));
    })
    .catch(error => {
      window.GP_HANDSHAKE_READY = false;
      const button = document.getElementById('search-button');
      if (button) { button.disabled = true; button.textContent = 'Live-Suche gesperrt'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className='compact-status error'; state.textContent=`Controller konnte nicht geladen werden: ${error.message || error}`; }
    });
})();
