(() => {
  'use strict';

  const markCard = card => {
    if (!(card instanceof HTMLElement) || !card.classList.contains('listing')) return;
    const link = card.querySelector('h3 a, a[href]');
    if (!link) return;
    let source = 'kleinanzeigen';
    try {
      const host = new URL(link.href, location.href).hostname.toLowerCase();
      if (host.includes('vinted.')) source = 'vinted';
      else if (host.includes('kleinanzeigen.')) source = 'kleinanzeigen';
      else return;
    } catch { return; }

    card.classList.remove('source-kleinanzeigen', 'source-vinted');
    card.classList.add(`source-${source}`);
    if (!card.querySelector('.source-badge')) {
      const body = card.children[1] || card;
      const badge = document.createElement('span');
      badge.className = 'source-badge';
      badge.textContent = source === 'vinted' ? 'Vinted' : 'Kleinanzeigen';
      body.insertBefore(badge, body.firstChild);
    }
  };

  const scan = root => {
    if (root instanceof HTMLElement && root.classList.contains('listing')) markCard(root);
    root.querySelectorAll?.('.listing').forEach(markCard);
  };

  const results = document.getElementById('results');
  if (!results) return;
  scan(results);
  new MutationObserver(records => {
    for (const record of records) for (const node of record.addedNodes) if (node.nodeType === 1) scan(node);
  }).observe(results, {childList: true, subtree: true});
})();
