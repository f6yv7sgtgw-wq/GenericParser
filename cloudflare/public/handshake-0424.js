(() => {
  'use strict';
  const I=window.GP_BUILD_IDENTITY;
  if(!I) throw new Error('Shared build identity missing');
  const el=id=>document.getElementById(id);
  window.GP_BUILD=I;window.GP_HANDSHAKE_READY=false;
  const log=(type,message,data={})=>window.gpEventLog?.(type,message,{uiVersion:I.version,uiBuild:I.buildId,...data});
  function setEnabled(enabled){const search=el('search-button'),resume=el('resume-button');if(search){search.disabled=!enabled;search.textContent=enabled?'Live-Suche starten':'Live-Suche gesperrt';}if(resume)resume.disabled=!enabled;}
  function render(ok,title,detail){const badge=el('worker-version'),connection=el('connection'),text=el('worker-state-text');if(badge)badge.textContent=ok?I.version:'nicht bereit';if(connection){connection.classList.toggle('offline',!ok);connection.innerHTML=`<span></span> ${ok?'Bereit':'Deployment prüfen'}`;}if(text){text.className=`diagnostic ${ok?'done':'error'}`;text.innerHTML=`<span><strong>${title}</strong></span><span>${detail}</span>`;}}
  async function handshake(){setEnabled(false);render(false,'Versionsprüfung läuft',`${I.version} · ${I.buildId}`);try{await window.GP_CONTROLLER_READY;if(window.GP_CONTROLLER_VERSION!==I.version)throw new Error('Controller-Version abweichend');const r=await fetch(`./api/version?build=${encodeURIComponent(I.buildId)}`,{cache:'no-store'});const d=await r.json();const ok=r.ok&&d.version===I.version&&d.build_id===I.buildId&&d.api_contract===I.apiContract&&d.search_ready===true;if(!ok)throw new Error(`Worker ${d.version||'?'} / ${d.build_id||'?'}`);window.GP_HANDSHAKE_READY=true;setEnabled(true);render(true,'Deployment konsistent',`UI, Controller, Worker und Eventlog ${I.version} · ${I.buildId}`);log('deployment_handshake_ok','Gemeinsame Build-Identität bestätigt',{controllerVersion:window.GP_CONTROLLER_VERSION,workerVersion:d.version,buildId:d.build_id,eventLogKey:I.eventLogKey});}catch(e){window.GP_HANDSHAKE_READY=false;setEnabled(false);render(false,'Deployment nicht konsistent',String(e?.message||e));log('deployment_handshake_failed','Live-Suche wurde gesperrt',{error:String(e?.message||e)});}}
  handshake();
})();
