(() => {
  'use strict';
  const I=window.GP_BUILD_IDENTITY;
  if(!I) throw new Error('Shared build identity missing');
  const el=id=>document.getElementById(id);
  const log=(t,m,d={})=>window.gpEventLog?.(t,m,{uiVersion:I.version,uiBuild:I.buildId,...d});
  function setReady(ok){
    window.GP_HANDSHAKE_READY=ok;
    const b=el('search-button'),r=el('resume-button');
    if(b){b.disabled=!ok;b.textContent=ok?'Live-Suche starten':'Live-Suche gesperrt';}
    if(r)r.disabled=!ok;
  }
  function render(ok,title,lines){
    const badge=el('worker-version'),c=el('connection'),box=el('worker-state-text');
    if(badge)badge.textContent=ok?I.version:'nicht bereit';
    if(c){c.classList.toggle('offline',!ok);c.innerHTML=`<span></span> ${ok?'Bereit':'Deployment prüfen'}`;}
    if(box){box.className=`diagnostic ${ok?'done':'error'}`;box.innerHTML=`<span><strong>${title}</strong></span>${lines.map(x=>`<span>${x}</span>`).join('')}`;}
  }
  async function run(){
    setReady(false);
    render(false,'Datenfluss wird geprüft',[`${I.version} · ${I.buildId}`]);
    try{
      await window.GP_CONTROLLER_READY;
      const u=new URL('./api/version',location.href);u.searchParams.set('build',I.buildId);
      const r=await fetch(u,{cache:'no-store',headers:{Accept:'application/json'}});
      const d=await r.json();
      const checks={version:d.version===I.version,build:d.build_id===I.buildId,contract:d.api_contract===I.apiContract,entrypoint:d.entrypoint===I.entrypoint,bootstrap:d.bootstrap_module===I.bootstrapModule,search:d.search_module===I.searchModule};
      if(!r.ok||!Object.values(checks).every(Boolean)) throw new Error(`Abweichung: ${Object.entries(checks).filter(([,v])=>!v).map(([k])=>k).join(', ')}`);
      setReady(true);
      render(true,'Datenfluss konsistent',[`UI/Controller ${I.version}/${I.buildId}`,`Worker ${d.version}/${d.build_id}`,`Vertrag ${d.api_contract}`,`Search ${d.search_module}`]);
      log('deployment_handshake_ok','0.43.2 Datenfluss bestätigt',{checks,worker:d,handshakeReady:true});
    }catch(e){
      setReady(false);
      render(false,'Deployment nicht konsistent',[String(e?.message||e)]);
      log('deployment_handshake_failed','Live-Suche wurde gesperrt',{error:String(e?.message||e),handshakeReady:false});
    }
  }
  run();
})();