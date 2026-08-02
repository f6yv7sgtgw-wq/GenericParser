(() => {
  'use strict';
  const LOG_KEY='generic-parser-eventlog-0406';
  const add=(type,message,data={})=>{const rows=JSON.parse(localStorage.getItem(LOG_KEY)||'[]');rows.push({time:new Date().toISOString(),type,message,...data});localStorage.setItem(LOG_KEY,JSON.stringify(rows.slice(-500)));};
  window.gpEventLog=add;
  let active=false, stopAfterPage=false, cooling=false;
  const nativeFetch=window.fetch.bind(window);
  window.fetch=async(input,init={})=>{const url=typeof input==='string'?input:input?.url||'',isSearch=/\/api\/search(?:\?|$)/.test(url);if(isSearch){active=true;add('request','Seitenanfrage gestartet',{query:document.getElementById('query')?.value||'',url});}try{const response=await nativeFetch(input,init);if(isSearch)add('response','Seitenanfrage beendet',{status:response.status,phase:response.headers.get('X-GenericParser-Phase'),elapsed:response.headers.get('X-GenericParser-Elapsed-Ms')});return response;}catch(error){if(isSearch)add('error','Netzwerkfehler',{name:error?.name,message:error?.message});throw error;}finally{if(isSearch)active=false;}};
  const stop=document.getElementById('stop-button');
  if(stop){const clone=stop.cloneNode(true);stop.replaceWith(clone);clone.addEventListener('click',()=>{stopAfterPage=true;stopRequested=true;clone.disabled=true;clone.textContent=active?'Aktuelle Seite wird beendet …':'Suche wird beendet …';workerState('Stopp angefordert',active?'Aktuelle Seite läuft kontrolliert zu Ende.':'Suchschleife wird beendet.','working');add('stop_requested','Sanfter Stopp angefordert',{query:document.getElementById('query')?.value||'',activeRequest:active});});}
  const search=document.getElementById('search-button');
  if(search){search.addEventListener('click',async e=>{if(cooling){e.preventDefault();e.stopImmediatePropagation();return;}if(stopAfterPage){e.preventDefault();e.stopImmediatePropagation();cooling=true;search.disabled=true;workerState('Abkühlpause','Neue Suche startet in 2 Sekunden.','working');add('cooldown','Abkühlpause gestartet');await new Promise(r=>setTimeout(r,2000));stopAfterPage=false;cooling=false;search.disabled=false;search.click();return;}add('search_start','Neue Suche gestartet',{query:document.getElementById('query')?.value||''});},true);}
  const originalWorkerState=window.workerState;
  window.workerState=function(title,detail,kind=''){add('status',title,{detail,kind});return originalWorkerState(title,detail,kind);};
  window.addEventListener('error',e=>add('browser_error',e.message,{file:e.filename,line:e.lineno,column:e.colno}));
  window.addEventListener('unhandledrejection',e=>add('promise_rejection',String(e.reason?.message||e.reason)));
})();