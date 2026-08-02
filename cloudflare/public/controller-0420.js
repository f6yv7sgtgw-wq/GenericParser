(() => {
  'use strict';
  const SOURCE='./controller-0411.js?v=0.420-source';
  const replacements=[
    ["const VERSION = '0.41.1';","const VERSION = '0.42.0';"],
    ["const BUILD_ID = 'gp-0411-20260802-1';","const BUILD_ID = 'gp-0420-20260802-1';"],
    ["const LOG_KEY = 'generic-parser-eventlog-0411';","const LOG_KEY = 'generic-parser-eventlog-0420';"]
  ];
  window.GP_CONTROLLER_READY=fetch(SOURCE,{cache:'no-store'})
    .then(response=>{if(!response.ok)throw new Error(`Controller-Quelle HTTP ${response.status}`);return response.text();})
    .then(source=>{
      for(const [from,to] of replacements){
        if(!source.includes(from))throw new Error(`Controller-Konstante fehlt: ${from}`);
        source=source.replace(from,to);
      }
      if(/0\.41\.1|gp-0411-20260802-1|eventlog-0411/.test(source))throw new Error('Controller enthält nach der Transformation alte Build-Kennungen.');
      Function(`${source}\n//# sourceURL=controller-0420-runtime.js`)();
      window.GP_CONTROLLER_VERSION='0.42.0';
      return true;
    })
    .catch(error=>{
      window.GP_CONTROLLER_ERROR=String(error?.message||error);
      const badge=document.getElementById('worker-version');
      const text=document.getElementById('worker-state-text');
      if(badge)badge.textContent='Controllerfehler';
      if(text)text.innerHTML=`<span><strong>Controller 0.42.0 nicht geladen</strong></span><span>${String(error?.message||error)}</span>`;
      throw error;
    });
})();
