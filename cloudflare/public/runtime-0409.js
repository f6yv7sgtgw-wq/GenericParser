(() => {
  'use strict';
  const VERSION='0.40.9';
  const badge=document.getElementById('worker-version');
  if(badge) badge.textContent=VERSION;
  const oldLog=window.gpEventLog;
  window.gpEventLog=(type,message,data={})=>{
    const enriched={...data,uiVersion:VERSION};
    return typeof oldLog==='function'?oldLog(type,message,enriched):undefined;
  };
  window.addEventListener('load',()=>{
    const b=document.getElementById('worker-version');
    if(b&&!b.textContent.trim())b.textContent=VERSION;
  });
})();
