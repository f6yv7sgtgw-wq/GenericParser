(() => {
  'use strict';
  const I=window.GP_BUILD_IDENTITY;
  if(!I) throw new Error('Shared build identity missing');
  const SOURCE='./controller-0411.js?v=0.427-source';
  window.GP_CONTROLLER_READY=fetch(new URL(SOURCE,window.location.href),{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`Controller-Quelle HTTP ${r.status}`);return r.text();}).then(source=>{
    const replacements=[
      ["const VERSION = '0.41.1';",`const VERSION = '${I.version}';`],
      ["const BUILD_ID = 'gp-0411-20260802-1';",`const BUILD_ID = '${I.buildId}';`],
      ["const LOG_KEY = 'generic-parser-eventlog-0411';",`const LOG_KEY = '${I.eventLogKey}';`]
    ];
    for(const [from,to] of replacements){if(!source.includes(from))throw new Error(`Controller-Konstante fehlt: ${from}`);source=source.replace(from,to);}
    Function(`${source}\n//# sourceURL=controller-0427-runtime.js`)();
    const delay=document.getElementById('page-delay');
    if(delay){delay.value='5000';delay.disabled=true;}
    window.GP_CONTROLLER_VERSION=I.version;
    window.dispatchEvent(new CustomEvent('gp-controller-ready',{detail:I}));
    return true;
  });
})();
