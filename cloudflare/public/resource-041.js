(() => {
  'use strict';
  const VERSION='0.41.0';
  const LOG_KEY='generic-parser-eventlog-0408';
  const nativeFetch=window.fetch.bind(window);
  const safe=v=>{try{return JSON.parse(v)}catch{return null}};
  const add=(type,message,data={})=>{
    try{
      const rows=safe(localStorage.getItem(LOG_KEY)||'[]')||[];
      rows.push({time:new Date().toISOString(),epoch:Date.now(),type,message,...data,uiVersion:VERSION});
      localStorage.setItem(LOG_KEY,JSON.stringify(rows.slice(-500)));
    }catch(error){console.warn('Ressourcenlog konnte nicht geschrieben werden',error)}
  };
  const badge=document.getElementById('worker-version');
  if(badge)badge.textContent=VERSION;
  const workerCard=document.getElementById('worker-state');
  if(workerCard){
    const card=document.createElement('section');
    card.id='resource-card';
    card.className='card';
    card.innerHTML='<div class="row between"><h2>Ressourcen pro Seite</h2><span class="chip">0.41</span></div><div id="resource-state" class="diagnostic"><span>Noch keine Messung</span><span>Heap: nicht verfügbar</span></div>';
    workerCard.insertAdjacentElement('afterend',card);
  }
  const render=m=>{
    const box=document.getElementById('resource-state');
    if(!box||!m)return;
    const entries=[
      ['Gesamt',m.request_wall_ms,'ms'],['CPU',m.process_cpu_ms,'ms'],
      ['HTML-Fetch',m.html_fetch_ms,'ms'],['HTML-Parse',m.html_parse_ms,'ms'],
      ['HTML-Größe',m.html_bytes,'Bytes'],['Mobile',m.mobile_total_ms,'ms'],
      ['Mobile-Größe',m.mobile_response_bytes,'Bytes'],['Karten',m.parsed_cards??m.mobile_cards,'']
    ].filter(([,v])=>v!==null&&v!==undefined);
    entries.push(['Heap','nicht verfügbar','']);
    box.innerHTML=entries.map(([k,v,u])=>`<span>${k}: ${v}${u?' '+u:''}</span>`).join('');
  };
  window.fetch=async function resourceFetch(input,init){
    const url=typeof input==='string'?input:input?.url||'';
    const response=await nativeFetch(input,init);
    if(!/\/api\/search(?:\?|$)/.test(url))return response;
    const raw=response.headers.get('X-GenericParser-Resources');
    const version=response.headers.get('X-GenericParser-Version');
    if(version&&badge)badge.textContent=version;
    const metrics=safe(raw||'');
    if(metrics){
      render(metrics);
      add('resource_metrics','Ressourcenmessung abgeschlossen',{query:document.getElementById('query')?.value||'',status:response.status,workerVersion:version||null,metrics});
    }else{
      add('resource_metrics_missing','Keine Ressourcenheader erhalten',{query:document.getElementById('query')?.value||'',status:response.status,contentType:response.headers.get('content-type')||null});
    }
    return response;
  };
})();
