(() => {
  'use strict';
  const SOURCE='./controller-0411.js?v=0.423-source';
  const replacements=[
    ["const VERSION = '0.41.1';","const VERSION = '0.42.3';"],
    ["const BUILD_ID = 'gp-0411-20260802-1';","const BUILD_ID = 'gp-0423-20260802-1';"],
    ["const LOG_KEY = 'generic-parser-eventlog-0411';","const LOG_KEY = 'generic-parser-eventlog-0423';"]
  ];
  window.GP_CONTROLLER_READY=fetch(SOURCE,{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`Controller-Quelle HTTP ${r.status}`);return r.text();}).then(source=>{
    for(const [from,to] of replacements){if(!source.includes(from))throw new Error(`Controller-Konstante fehlt: ${from}`);source=source.replace(from,to);}
    if(/0\.41\.1|gp-0411-20260802-1|eventlog-0411/.test(source))throw new Error('Controller enthält alte Build-Kennungen.');
    Function(`${source}\n//# sourceURL=controller-0423-runtime.js`)();
    window.GP_CONTROLLER_VERSION='0.42.3';
    window.dispatchEvent(new CustomEvent('gp-controller-ready',{detail:{version:'0.42.3',buildId:'gp-0423-20260802-1'}}));
    return true;
  }).catch(error=>{window.GP_CONTROLLER_ERROR=String(error?.message||error);throw error;});
})();
