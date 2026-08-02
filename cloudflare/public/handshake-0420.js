(() => {
  'use strict';
  const UI_VERSION='0.42.0';
  const BUILD_ID='gp-0420-20260802-1';
  const API_CONTRACT='match-v6.1-page-worker';
  window.GP_BUILD=Object.freeze({version:UI_VERSION,buildId:BUILD_ID,apiContract:API_CONTRACT});
  window.GP_HANDSHAKE_READY=false;

  const versionBadge=document.getElementById('worker-version');
  const connection=document.getElementById('connection');
  const searchButton=document.getElementById('search-button');
  const resumeButton=document.getElementById('resume-button');
  const workerText=document.getElementById('worker-state-text');
  let ready=false;

  function setBlocked(blocked){
    if(searchButton){searchButton.disabled=blocked;searchButton.textContent=blocked?'Live-Suche gesperrt':'Live-Suche starten';}
    if(resumeButton)resumeButton.disabled=blocked;
  }
  function render(title,detail,ok){
    if(versionBadge)versionBadge.textContent=ok?UI_VERSION:'nicht bereit';
    if(connection){connection.classList.toggle('offline',!ok);connection.innerHTML=`<span></span> ${ok?'Bereit':'Deployment prüfen'}`;}
    if(workerText){workerText.className=`diagnostic ${ok?'done':'error'}`;workerText.innerHTML=`<span><strong>${title}</strong></span><span>${detail}</span>`;}
  }

  async function handshake(){
    ready=false;window.GP_HANDSHAKE_READY=false;setBlocked(true);
    render('Bootstrap-Prüfung läuft',`UI ${UI_VERSION} · Build ${BUILD_ID}`,false);
    try{
      await window.GP_CONTROLLER_READY;
      if(window.GP_CONTROLLER_VERSION!==UI_VERSION)throw new Error(`Controller ${window.GP_CONTROLLER_VERSION||'unbekannt'} statt ${UI_VERSION}`);
      const response=await fetch(`./api/version?build=${encodeURIComponent(BUILD_ID)}`,{method:'GET',cache:'no-store',headers:{Accept:'application/json','X-GenericParser-UI-Version':UI_VERSION,'X-GenericParser-UI-Build':BUILD_ID}});
      const contentType=response.headers.get('content-type')||'';
      const data=contentType.includes('application/json')?await response.json():null;
      const version=data?.version||response.headers.get('X-GenericParser-Version');
      const buildId=data?.build_id||response.headers.get('X-GenericParser-Build');
      const contract=data?.api_contract||response.headers.get('X-GenericParser-Contract');
      const bootstrap=response.headers.get('X-GenericParser-Bootstrap')||data?.worker_unit;
      const consistent=response.ok&&data?.search_ready===true&&version===UI_VERSION&&buildId===BUILD_ID&&contract===API_CONTRACT&&String(bootstrap).includes('lazy');
      if(!consistent)throw new Error(`UI ${UI_VERSION}/${BUILD_ID} · Worker ${version||'unbekannt'}/${buildId||'unbekannt'} · Vertrag ${contract||'unbekannt'} · Bootstrap ${bootstrap||'unbekannt'}`);
      ready=true;window.GP_HANDSHAKE_READY=true;setBlocked(false);
      render('Deployment konsistent',`UI, Controller und Worker ${UI_VERSION} · ${BUILD_ID} · Lazy-Bootstrap bereit`,true);
      window.gpEventLog?.('deployment_handshake_ok','0.42.0-Datenfluss ist konsistent',{uiVersion:UI_VERSION,controllerVersion:window.GP_CONTROLLER_VERSION,workerVersion:version,buildId,apiContract:contract,bootstrap,searchModuleLoaded:Boolean(data?.search_module_loaded)});
    }catch(error){
      setBlocked(true);render('Deployment nicht konsistent',String(error?.message||error),false);
      window.gpEventLog?.('deployment_handshake_failed','Live-Suche wurde gesperrt',{uiVersion:UI_VERSION,buildId:BUILD_ID,error:String(error?.message||error)});
    }
  }
  document.addEventListener('click',event=>{const target=event.target instanceof Element?event.target.closest('#search-button,#resume-button'):null;if(!target||ready)return;event.preventDefault();event.stopImmediatePropagation();render('Suche gesperrt','Controller, UI und Lazy-Bootstrap müssen zuerst denselben Build bestätigen.',false);},true);
  window.addEventListener('pageshow',event=>{if(event.persisted)handshake();});
  handshake();
})();
