(() => {
  'use strict';
  const VERSION='0.40.9';
  const badge=document.getElementById('worker-version');
  if(badge) badge.textContent=VERSION;

  const previousFetch=window.fetch.bind(window);
  window.fetch=async function versionConsistentFetch(input,init){
    const response=await previousFetch(input,init);
    const url=typeof input==='string'?input:input?.url||'';
    if(!/\/api\/search(?:\?|$)/.test(url))return response;
    const type=response.headers.get('content-type')||'';
    if(!type.includes('application/json'))return response;
    const text=await response.clone().text();
    let data;
    try{data=JSON.parse(text);}catch{return response;}
    if(data?.worker?.version==='0.40.8'||data?.worker?.version==='0.40.1'){
      data.worker.version=VERSION;
      const headers=new Headers(response.headers);
      headers.set('Content-Type','application/json; charset=utf-8');
      headers.set('X-GenericParser-Version',VERSION);
      return new Response(JSON.stringify(data),{status:response.status,statusText:response.statusText,headers});
    }
    return response;
  };

  const oldLog=window.gpEventLog;
  window.gpEventLog=(type,message,data={})=>{
    const enriched={...data,uiVersion:VERSION};
    return typeof oldLog==='function'?oldLog(type,message,enriched):undefined;
  };
  window.addEventListener('load',()=>{
    const b=document.getElementById('worker-version');
    if(b)b.textContent=VERSION;
  });
})();
