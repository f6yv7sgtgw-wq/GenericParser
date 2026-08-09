(() => {
  'use strict';

  const sourceFromLink = link => {
    try {
      const host = new URL(link.href, location.href).hostname.toLowerCase();
      if (host.includes('ebay.')) return 'ebay';
      if (host.includes('vinted.')) return 'vinted';
      if (host.includes('kleinanzeigen.')) return 'kleinanzeigen';
    } catch {}
    return null;
  };

  const markCard = card => {
    if (!(card instanceof HTMLElement) || !card.classList.contains('listing')) return;
    const link = card.querySelector('h3 a, a[href]');
    const source = link ? sourceFromLink(link) : null;
    if (!source) return;
    card.classList.remove('source-kleinanzeigen', 'source-vinted', 'source-ebay');
    card.classList.add(`source-${source}`);
    const badge = card.querySelector('.source-badge');
    if (badge) badge.textContent = source === 'ebay' ? 'eBay' : source === 'vinted' ? 'Vinted' : 'Kleinanzeigen';
  };

  const scan = root => {
    if (root instanceof HTMLElement && root.classList.contains('listing')) markCard(root);
    root.querySelectorAll?.('.listing').forEach(markCard);
  };

  const results = document.getElementById('results');
  if (!results) return;
  scan(results);
  new MutationObserver(records => {
    for (const record of records) {
      for (const node of record.addedNodes) if (node.nodeType === 1) scan(node);
    }
  }).observe(results, {childList: true, subtree: true});
})();
