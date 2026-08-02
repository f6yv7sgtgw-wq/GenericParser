const $ = id => document.getElementById(id);
const apiUrl = path => new URL(path.replace(/^\//, ''), location.href).toString();
const list = id => $(id).value.split(',').map(value => value.trim()).filter(value => value && value !== '0');
const num = id => $(id).value.trim() === '' ? null : Number($(id).value);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

let maxResultsExplicit = false;
let stopRequested = false;

function msg(text, error = false) {
  $('message').textContent = text;
  $('message').className = 'message' + (error ? ' error' : '');
}
function clearMessage() { $('message').className = 'message hidden'; }
function esc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}
function headers() {
  const token = $('token').value.trim();
  localStorage.setItem('gp-token', token);
  return {'Content-Type':'application/json', ...(token ? {'X-GenericParser-Token':token} : {})};
}
function metric(value, label) { return `<div class="metric"><strong>${esc(value)}</strong><span>${esc(label)}</span></div>`; }
function workerState(title, detail, kind = '') {
  const box = $('worker-state-text');
  box.className = 'diagnostic ' + kind;
  box.innerHTML = `<span><strong>${esc(title)}</strong></span><span>${esc(detail)}</span>`;
}

function baseBody() {
  const payload = {mode:'live', query:$('query').value.trim()};
  const add = (key, value) => {
    if (value !== null && value !== '' && !(Array.isArray(value) && !value.length)) payload[key] = value;
  };
  const postalCode = $('postal-code').value.trim();
  const locationId = num('location-id');
  add('postal_code', postalCode);
  add('location_id', locationId);
  if (postalCode || locationId) add('radius_km', num('radius-km'));
  add('required_terms', list('required-terms'));
  add('excluded_terms', list('excluded-terms'));
  add('model_patterns', list('model-patterns'));
  add('brands', list('brands'));
  if (num('max-price') > 0) add('max_price', num('max-price'));
  if (num('market-value') > 0) add('market_value', num('market-value'));
  payload.accept_bundles = $('accept-bundles').checked;
  payload.accept_incomplete = $('accept-incomplete').checked;
  payload.include_review = $('include-review').checked;
  payload.include_rejected = $('include-rejected').checked;
  payload.sort_by = $('sort-by').value;
  return payload;
}

function matchOf(item) {
  const match = item && typeof item.match === 'object' && item.match ? item.match : {};
  return {
    score:Number(match.score ?? item.score ?? 0),
    decision:String(match.decision ?? item.decision ?? 'review'),
    listingClass:String(match.listing_class ?? item.listing_class ?? 'produkt'),
    reason:String(match.reason ?? item.reason ?? 'Keine Bewertungsdetails verfügbar')
  };
}
function card(item) {
  const match = matchOf(item);
  return `<article class="listing"><div class="listing-image">${item.image_url ? `<img src="${esc(item.image_url)}" loading="lazy">` : 'KEIN BILD'}</div><div><div class="row between"><span class="chip">${esc(match.listingClass)}</span><strong>${match.score}/100 · ${esc(match.decision)}</strong></div><h3><a href="${esc(item.url)}" target="_blank">${esc(item.title)}</a></h3><div class="price">${item.price != null ? esc(item.price) + ' €' : esc(item.price_raw || 'Preis offen')}</div><div class="meta">${esc([item.postal_code,item.place].filter(Boolean).join(' '))}</div><p>${esc(match.reason)}</p></div></article>`;
}
function sorted(items, mode) {
  const result = [...items];
  if (mode === 'date') return result.sort((a,b) => String(b.posted_at || '').localeCompare(String(a.posted_at || '')));
  if (mode === 'price_asc') return result.sort((a,b) => (Number(a.price) || Infinity) - (Number(b.price) || Infinity));
  if (mode === 'price_desc') return result.sort((a,b) => (Number(b.price) || -Infinity) - (Number(a.price) || -Infinity));
  return result.sort((a,b) => Number(b.score || b.match?.score || 0) - Number(a.score || a.match?.score || 0));
}

function renderState(state, worker) {
  const items = sorted([...state.items.values()], $('sort-by').value);
  $('summary').classList.remove('hidden');
  let metrics = '';
  if (state.reportedTotal != null) metrics += metric(state.reportedTotal.toLocaleString('de-DE'), 'Kleinanzeigen meldet');
  metrics += metric(items.length, 'eindeutig') + metric(state.pages, 'Seiten') + metric(state.requests, 'Anfragen') + metric(state.duplicates, 'Duplikate') + metric(state.malformed, 'verworfen');
  $('summary').innerHTML = metrics;
  $('diagnostics-card').classList.remove('hidden');
  $('worker-version').textContent = worker?.version ?? '0.39.2';
  $('urls').innerHTML = state.url ? `<code>${esc(state.url)}</code>` : '';
  const status = state.error ? 'Fehler' : state.running ? 'arbeitet' : state.stopped ? 'gestoppt' : state.complete ? 'vollständig' : 'bereit';
  $('diagnostics').innerHTML = `<div class="diagnostic"><span>Quelle: ${esc(state.source)}</span><span>Status: ${status}</span><span>Aktuelle Seite: ${state.page + 1}</span><span>Seitenziel: ${state.pageLimit >= 500 ? 'bis Ende' : state.pageLimit}</span><span>Anfragen: ${state.requests}</span><span>Stopp: ${esc(state.stopReason || '–')}</span></div>` + state.history.map(entry => `<div class="diagnostic"><span>Seite ${entry.page + 1}</span><span>${entry.count} gültig</span><span>${entry.malformed} verworfen</span><span>${esc(entry.reason)}</span></div>`).join('');
  $('results').innerHTML = items.map(card).join('');
}

function safeError(status, text, data) {
  if (data && typeof data === 'object') {
    const detail = data.detail;
    return Array.isArray(detail) ? detail.map(item => item.msg || String(item)).join(', ') : String(detail || `API-Fehler ${status}`);
  }
  if (/worker exceeded resource limits/i.test(text)) return 'Cloudflare-Ressourcenlimit erreicht.';
  if (/<html|<!doctype/i.test(text)) return `HTML-Fehlerseite statt Suchdaten (HTTP ${status}).`;
  return text.slice(0, 300) || `API-Fehler ${status}`;
}
async function requestPage(payload) {
  const response = await fetch(apiUrl('api/search'), {method:'POST', headers:headers(), body:JSON.stringify(payload)});
  const text = await response.text();
  let data = null;
  try { data = JSON.parse(text); } catch {}
  if (!response.ok) throw new Error(safeError(response.status, text, data));
  if (!data || !Array.isArray(data.listings) || !data.pagination) throw new Error('Der Worker lieferte keine gültige Seitenantwort.');
  return data;
}

async function pauseWithStatus(milliseconds, nextPage, loaded) {
  const started = Date.now();
  while (!stopRequested) {
    const remaining = milliseconds - (Date.now() - started);
    if (remaining <= 0) break;
    workerState('Worker wartet', `Nächste Seite ${nextPage + 1} in ${(remaining / 1000).toFixed(1).replace('.', ',')} s · ${loaded} Ergebnisse geladen`, 'working');
    await sleep(Math.min(100, remaining));
  }
}

async function search() {
  clearMessage();
  stopRequested = false;
  $('search-button').textContent = 'Suche läuft …';
  $('search-button').disabled = true;
  $('stop-button').classList.remove('hidden');
  $('stop-button').disabled = false;

  const base = baseBody();
  const resultLimit = maxResultsExplicit && num('max-results') > 0 ? num('max-results') : null;
  const pageLimit = Number($('search-scope').value || 20);
  const pageDelay = Number($('page-delay').value || 400);
  const state = {items:new Map(), page:0, pages:0, requests:0, duplicates:0, malformed:0, source:'auto', reportedTotal:null, complete:false, running:true, stopped:false, error:false, stopReason:'', url:'', history:[], pageLimit};
  let worker = null;

  try {
    while (!state.complete && state.pages < pageLimit && state.page < 500) {
      if (stopRequested) {
        state.stopped = true;
        state.stopReason = 'user_stopped';
        break;
      }
      if (resultLimit !== null && state.items.size >= resultLimit) {
        state.complete = true;
        state.stopReason = 'user_limit_reached';
        break;
      }

      workerState('Worker arbeitet', `Seite ${state.page + 1} wird verarbeitet · ${state.items.size} Ergebnisse geladen`, 'working');
      const payload = {...base, page:state.page, source:state.source};
      let data;
      try {
        data = await requestPage(payload);
      } catch (firstError) {
        workerState('Worker wiederholt', `Seite ${state.page + 1} wird nach kurzer Pause erneut versucht`, 'working');
        await pauseWithStatus(800, state.page, state.items.size);
        if (stopRequested) throw firstError;
        data = await requestPage(payload);
      }

      worker = data.worker;
      state.requests++;
      state.pages++;
      state.source = data.pagination.source || state.source;
      state.stopReason = data.pagination.stop_reason || '';
      state.url = (data.generated_urls || [])[0] || state.url;
      if (data.summary?.reported_total != null) state.reportedTotal = Number(data.summary.reported_total);
      state.malformed += Number(data.summary?.malformed_rejected || 0);

      let added = 0;
      for (const item of data.listings) {
        const id = String(item.id);
        if (!state.items.has(id)) { state.items.set(id, item); added++; }
        else state.duplicates++;
      }
      state.history.push({page:state.page, count:Number(data.pagination.unique_listings || 0), malformed:Number(data.summary?.malformed_rejected || 0), reason:state.stopReason});
      workerState('Worker fertig', `Seite ${state.page + 1} abgeschlossen · ${added} neue Ergebnisse`, 'done');
      state.complete = data.pagination.complete === true || data.pagination.next_page == null;
      state.page = data.pagination.next_page ?? state.page;
      renderState(state, worker);

      if (resultLimit !== null && state.items.size >= resultLimit) {
        state.complete = true;
        state.stopReason = 'user_limit_reached';
      }
      if (!state.complete && state.pages < pageLimit) {
        msg(`Kurze Pause vor Seite ${state.page + 1} · ${state.items.size} eindeutige Ergebnisse`);
        await pauseWithStatus(pageDelay, state.page, state.items.size);
      }
    }

    if (stopRequested) {
      state.stopped = true;
      state.stopReason = 'user_stopped';
    } else if (!state.complete && state.pages >= pageLimit) {
      state.stopped = true;
      state.stopReason = 'page_limit_reached';
    }

    state.running = false;
    renderState(state, worker);
    if (state.stopped) {
      workerState('Worker fertig', `Suche beendet · ${state.items.size} Ergebnisse nach ${state.pages} Seiten`, 'done');
      msg(`Suche nach ${state.pages} Seiten beendet. ${state.items.size}${state.reportedTotal ? ` von ${state.reportedTotal.toLocaleString('de-DE')}` : ''} Ergebnisse geladen.`);
    } else if (!state.items.size) {
      workerState('Worker fertig', 'Keine Ergebnisse gefunden', 'done');
      msg('Keine Ergebnisse gefunden.');
    } else {
      workerState('Worker fertig', `Suche vollständig · ${state.items.size} eindeutige Ergebnisse`, 'done');
      msg(`${state.items.size}${state.reportedTotal ? ` von ${state.reportedTotal.toLocaleString('de-DE')}` : ''} Ergebnissen verarbeitet.`);
    }
  } catch (error) {
    state.running = false;
    state.error = true;
    renderState(state, worker);
    workerState('Worker abgebrochen', `${error.message} · ${state.items.size} Ergebnisse bleiben sichtbar`, 'error');
    msg(`${error.message} Bereits geladene Ergebnisse bleiben sichtbar.`, true);
  } finally {
    $('search-button').textContent = 'Live-Suche starten';
    $('search-button').disabled = false;
    $('stop-button').classList.add('hidden');
    $('stop-button').disabled = false;
  }
}

const ids = ['query','required-terms','excluded-terms','model-patterns','brands','max-price','market-value','postal-code','location-id','radius-km','max-results','sort-by','search-scope','page-delay','accept-bundles','accept-incomplete','include-review','include-rejected'];
function refreshProfiles() {
  const select = $('profiles');
  select.innerHTML = '<option value="">– auswählen –</option>';
  Object.keys(localStorage).filter(key => key.startsWith('gp-profile:')).sort().forEach(key => {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = key.slice(11);
    select.appendChild(option);
  });
}
function saveProfile() {
  const name = $('profile-name').value.trim() || 'Meine Suche';
  const data = {};
  ids.forEach(id => data[id] = $(id).type === 'checkbox' ? $(id).checked : $(id).value);
  localStorage.setItem('gp-profile:' + name, JSON.stringify(data));
  refreshProfiles();
  msg(`Profil „${name}“ gespeichert.`);
}

$('profiles').addEventListener('change', event => {
  if (!event.target.value) return;
  const data = JSON.parse(localStorage.getItem(event.target.value));
  Object.entries(data).forEach(([id,value]) => {
    if ($(id)) $(id).type === 'checkbox' ? $(id).checked = Boolean(value) : $(id).value = value;
  });
  const value = String(data['max-results'] ?? '').trim();
  maxResultsExplicit = value !== '' && Number(value) > 0;
  $('profile-name').value = event.target.value.slice(11);
});
$('search-button').addEventListener('click', search);
$('stop-button').addEventListener('click', () => {
  stopRequested = true;
  $('stop-button').disabled = true;
  workerState('Worker stoppt', 'Die aktuelle Seite wird beendet; danach wird nicht fortgesetzt.', 'working');
});
$('save-profile').addEventListener('click', saveProfile);
$('max-results').addEventListener('input', event => { if (event.isTrusted) maxResultsExplicit = event.target.value.trim() !== ''; });
$('demo-button').addEventListener('click', () => msg('Bitte eine Live-Suche starten.'));

const optional = ['profile-name','required-terms','excluded-terms','model-patterns','brands','max-price','market-value','postal-code','location-id','radius-km','max-results'];
optional.forEach(id => $(id).value = '');
$('query').value = '';
$('token').value = localStorage.getItem('gp-token') || '';
maxResultsExplicit = false;
refreshProfiles();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('./service-worker.js?v=0.392').catch(() => {});
