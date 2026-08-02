(() => {
  'use strict';
  const UI_VERSION='0.42.1';
  const BUILD_ID='gp-0421-20260802-1';
  const API_CONTRACT='match-v6.1-page-worker';
  const STATES=Object.freeze({BOOTING:'BOOTING',IDLE:'IDLE',BLOCKED:'BLOCKED'});
  let state=STATES.BOOTING;
  let ready=false;

  window.GP_BUILD=Object.freeze({version:UI_VERSION,buildId:BUILD_ID,apiContract:API_CONTRACT});
  window.GP_HANDSHAKE_READY=false;
  window.GP_UI_STATE=state;

  const el=id=>document.getElementById(id);

  function log(type,message,data={}){
    window.gpEventLog?.(type,message,{uiVersion:UI_VERSION,uiBuild:BUILD_ID,uiState:state,...data});
  }

  function setState(next,reason){
    const previous=state;
    state=next;
    window.GP_UI_STATE=next;
    const search=el('search-button');
    const resume=el('resume-button');
    const enabled=next===STATES.IDLE&&window.GP_HANDSHAKE_READY===true;
    if(search){search.disabled=!enabled;search.textContent=enabled?'Live-Suche starten':'Live-Suche gesperrt';}
    if(resume)resume.disabled=!enabled;
    log('ui_state_change','UI-Zustand geändert',{previousState:previous,nextState:next,reason,buttonFound:Boolean(search),buttonDisabled:search?.disabled??null,buttonEnabled:enabled});
  }

  function render(title,detail,ok){
    const badge=el('worker-version');
    const connection=el('connection');
    const workerText=el('worker-state-text');
    if(badge)badge.textContent=ok?UI_VERSION:'nicht bereit';
    if(connection){connection.classList.toggle('offline',!ok);connection.innerHTML=`<span></span> ${ok?'Bereit':'Deployment prüfen'}`;}
    if(workerText){workerText.className=`diagnostic ${ok?'done':'error'}`;workerText.innerHTML=`<span><strong>${title}</strong></span><span>${detail}</span>`;}
  }

  async function handshake(){
    ready=false;
    window.GP_HANDSHAKE_READY=false;
    setState(STATES.BOOTING,'handshake_started');
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

      ready=true;
      window.GP_HANDSHAKE_READY=true;
      setState(STATES.IDLE,'handshake_complete');
      render('Deployment konsistent',`UI, Controller und Worker ${UI_VERSION} · ${BUILD_ID} · Lazy-Bootstrap bereit`,true);
      log('deployment_handshake_ok','0.42.1-Datenfluss ist konsistent',{controllerVersion:window.GP_CONTROLLER_VERSION,workerVersion:version,buildId,apiContract:contract,bootstrap,searchModuleLoaded:Boolean(data?.search_module_loaded),buttonDisabled:el('search-button')?.disabled??null});
    }catch(error){
      window.GP_HANDSHAKE_READY=false;
      setState(STATES.BLOCKED,'handshake_failed');
      render('Deployment nicht konsistent',String(error?.message||error),false);
      log('deployment_handshake_failed','Live-Suche wurde gesperrt',{error:String(error?.message||error)});
    }
  }

  document.addEventListener('click',event=>{
    const target=event.target instanceof Element?event.target.closest('#search-button,#resume-button'):null;
    if(!target||ready)return;
    event.preventDefault();
    event.stopImmediatePropagation();
    render('Suche gesperrt','Controller, UI und Lazy-Bootstrap müssen zuerst denselben Build bestätigen.',false);
  },true);

  window.addEventListener('gp-controller-ready',()=>{
    if(ready){setState(STATES.IDLE,'controller_dom_replaced');}
  });
  window.addEventListener('pageshow',event=>{if(event.persisted)handshake();});
  handshake();
})();
