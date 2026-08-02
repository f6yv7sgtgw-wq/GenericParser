const $=id=>document.getElementById(id);const apiUrl=p=>new URL(p.replace(/^\//,''),location.href).toString();
const list=id=>$(id).value.split(',').map(x=>x.trim()).filter(Boolean);const num=id=>$(id).value.trim()===''?null:Number($(id).value);
function msg(t,e=false){$('message').textContent=t;$('message').className='message'+(e?' error':'');}function clear(){ $('message').className='message hidden'; }
function esc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function headers(){const t=$('token').value.trim();localStorage.setItem('gp-token',t);return {'Content-Type':'application/json',...(t?{'X-GenericParser-Token':t}:{})};}
function metric(v,l){return `<div class="metric"><strong>${v}</strong><span>${l}</span></div>`;}
function body(){
  const payload={mode:'live',query:$('query').value.trim()};
  const add=(key,value)=>{if(value!==null&&value!==''&&!(Array.isArray(value)&&value.length===0))payload[key]=value;};
  const pc=$('postal-code').value.trim(); const li=num('location-id');
  add('postal_code',pc); add('location_id',li); if(pc||li)add('radius_km',num('radius-km'));
  add('max_results',num('max-results')); add('required_terms',list('required-terms')); add('excluded_terms',list('excluded-terms'));
  add('model_patterns',list('model-patterns')); add('brands',list('brands')); add('max_price',num('max-price')); add('market_value',num('market-value'));
  payload.accept_bundles=$('accept-bundles').checked; payload.accept_incomplete=$('accept-incomplete').checked;
  payload.include_review=$('include-review').checked; payload.include_rejected=$('include-rejected').checked; payload.sort_by=$('sort-by').value;
  return payload;
}
function matchOf(x){
  const m=x&&typeof x.match==='object'&&x.match!==null?x.match:{};
  const score=Number.isFinite(Number(m.score??x.score))?Number(m.score??x.score):0;
  const decision=String(m.decision??x.decision??'review');
  const listingClass=String(m.listing_class??x.listing_class??'produkt');
  const positive=Array.isArray(m.positive_signals)?m.positive_signals:(Array.isArray(x.positive_signals)?x.positive_signals:[]);
  const warnings=Array.isArray(m.warnings)?m.warnings:(Array.isArray(x.warnings)?x.warnings:[]);
  const reason=String(m.reason??x.reason??'Keine Bewertungsdetails verfügbar');
  return {score,decision,listingClass,positive,warnings,reason};
}
function validPayload(p){
  if(!p||typeof p!=='object'||!Array.isArray(p.listings)||!p.summary||!p.worker){throw new Error('Ungültige API-Antwort: Pflichtfelder fehlen');}
  return p;
}
function render(payload){const p=validPayload(payload);clear();$('summary').classList.remove('hidden');$('summary').innerHTML=metric(p.summary.listings??0,'sichtbar')+metric(p.summary.raw_listings??0,'Rohfunde')+metric(p.summary.alerts??0,'Treffer')+metric(p.summary.review??0,'Prüfen')+metric(p.summary.rejected??0,'abgelehnt')+metric(p.summary.duplicates??0,'Duplikate');$('diagnostics-card').classList.remove('hidden');$('worker-version').textContent=p.worker.version??'unbekannt';$('urls').innerHTML=(p.generated_urls||[]).map(u=>`<code>${esc(u)}</code>`).join('');$('diagnostics').innerHTML=(p.diagnostics||[]).map(d=>`<div class="diagnostic"><span>${esc(d.state)}</span><span>${Number(d.cards_found??0)} Karten</span><span>${Number(d.listings_parsed??0)} geparst</span></div>`).join('');$('results').innerHTML=(p.listings||[]).map(x=>{const m=matchOf(x);return `<article class="listing"><div class="listing-image">${x.image_url?`<img src="${esc(x.image_url)}" loading="lazy">`:'KEIN BILD'}</div><div><div class="row between"><span class="chip">${esc(m.listingClass)}</span><strong>${m.score}/100 · ${esc(m.decision)}</strong></div><h3><a href="${esc(x.url)}" target="_blank">${esc(x.title)}</a></h3><div class="price">${x.price!==null&&x.price!==undefined?esc(x.price)+' €':esc(x.price_raw||'Preis offen')}</div><div class="meta">${esc([x.postal_code,x.place].filter(Boolean).join(' '))}</div><p>${esc(m.reason)}</p><div class="tags">${[...m.positive,...m.warnings].map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div></div></article>`}).join('');if(!p.listings.length)msg('Keine Treffer entsprechen dem aktuellen Profil.');}
async function search(){clear();$('search-button').textContent='Suche läuft …';$('search-button').disabled=true;try{const r=await fetch(apiUrl("api/search"),{method:'POST',headers:headers(),body:JSON.stringify(body())});const raw=await r.text();let d;try{d=JSON.parse(raw)}catch{d=raw}if(!r.ok)throw new Error(typeof d==='string'?d:(d.detail?.[0]?.msg||d.detail||JSON.stringify(d)));render(d);}catch(e){msg(e.message,true)}finally{$('search-button').textContent='Live-Suche starten';$('search-button').disabled=false}}
const ids=['query','required-terms','excluded-terms','model-patterns','brands','max-price','market-value','postal-code','location-id','radius-km','max-results','sort-by','accept-bundles','accept-incomplete','include-review','include-rejected'];
function refreshProfiles(){const s=$('profiles');s.innerHTML='<option value="">– auswählen –</option>';Object.keys(localStorage).filter(k=>k.startsWith('gp-profile:')).sort().forEach(k=>{const o=document.createElement('option');o.value=k;o.textContent=k.slice(11);s.appendChild(o)});}
function saveProfile(){const name=$('profile-name').value.trim()||'Meine Suche';const data={};ids.forEach(id=>data[id]=$(id).type==='checkbox'?$(id).checked:$(id).value);localStorage.setItem('gp-profile:'+name,JSON.stringify(data));refreshProfiles();msg(`Profil „${name}“ gespeichert.`)}
$('profiles').addEventListener('change',e=>{if(!e.target.value)return;const d=JSON.parse(localStorage.getItem(e.target.value));Object.entries(d).forEach(([id,v])=>{if($(id).type==='checkbox')$(id).checked=v;else $(id).value=v});$('profile-name').value=e.target.value.slice(11)});$('search-button').addEventListener('click',search);$('save-profile').addEventListener('click',saveProfile);const optionalText=['profile-name','required-terms','excluded-terms','model-patterns','brands','max-price','market-value','postal-code','location-id','radius-km','max-results']; optionalText.forEach(id=>$(id).value=''); $('query').value=''; $('token').value=localStorage.getItem('gp-token')||'';refreshProfiles();
if('serviceWorker'in navigator)navigator.serviceWorker.register("./service-worker.js").catch(()=>{});
$('demo-button').addEventListener('click',()=>msg('Demo entfällt in 0.32: Bitte eine Live-Suche oder ein gespeichertes Profil verwenden.'));
const standaloneFile = window.location.protocol === "file:";
