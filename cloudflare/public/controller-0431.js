(() => {
  'use strict';
  const I=window.GP_BUILD_IDENTITY;if(!I)throw new Error('Shared build identity missing');
  const SOURCE='./controller-0430.js?v=0.431-source';
  window.GP_CONTROLLER_READY=fetch(new URL(SOURCE,location.href),{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`Controller source HTTP ${r.status}`);return r.text();}).then(source=>{
    const replacements=[["0.43.0",I.version],["gp-0430-20260803-1",I.buildId],["match-v6.2-next-link-worker",I.apiContract],["generic-parser-eventlog-0430",I.eventLogKey]];
    for(const [from,to] of replacements)source=source.split(from).join(to);
    Function(`${source}\n//# sourceURL=controller-0431-runtime.js`)();
    window.GP_CONTROLLER_IDENTITY={version:I.version,buildId:I.buildId,apiContract:I.apiContract,module:'controller-0431.js'};
    window.dispatchEvent(new CustomEvent('gp-controller-ready',{detail:window.GP_CONTROLLER_IDENTITY}));
    return true;
  });
})();
