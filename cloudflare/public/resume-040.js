(() => {
  const button = document.getElementById('resume-button');
  if (!button) return;
  button.addEventListener('click', async event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    const raw = await dbGet();
    if (!raw) {
      msg('Kein gespeicherter Suchstand vorhanden.', true);
      return;
    }
    const state = restored(raw);
    state.pageLimit = Math.min(500, Number(state.pages || 0) + Number(document.getElementById('search-scope').value || 20));
    state.stopped = false;
    state.paused = false;
    state.complete = false;
    Object.entries(state.base || {}).forEach(([key, value]) => {
      const map = {query:'query',postal_code:'postal-code',location_id:'location-id',radius_km:'radius-km',max_price:'max-price',market_value:'market-value',required_terms:'required-terms',excluded_terms:'excluded-terms',model_patterns:'model-patterns',brands:'brands'};
      const id = map[key];
      const field = id && document.getElementById(id);
      if (field) field.value = Array.isArray(value) ? value.join(', ') : value;
    });
    await runSearch(state, true);
  }, true);
})();
