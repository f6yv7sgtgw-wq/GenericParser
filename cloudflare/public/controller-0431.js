(() => {
  'use strict';
  const I=window.GP_BUILD_IDENTITY;
  if(!I) throw new Error('Shared build identity missing');

  const bootstrapPromise=(async()=>{
    const sourceUrl=new URL('./controller-0430.js?v=0.431-source-fix1',location.href);
    const response=await fetch(sourceUrl,{cache:'no-store'});
    if(!response.ok) throw new Error(`Controller source HTTP ${response.status}`);

    let source=await response.text();
    const replacements=[
      ['0.43.0',I.version],
      ['gp-0430-20260803-1',I.buildId],
      ['match-v6.2-next-link-worker',I.apiContract],
      ['generic-parser-eventlog-0430',I.eventLogKey]
    ];
    for(const [from,to] of replacements) source=source.split(from).join(to);

    Function(`${source}\n//# sourceURL=controller-0431-runtime.js`)();

    // controller-0430 installs the real controller asynchronously and replaces
    // GP_CONTROLLER_READY with its own promise. The UI must not be enabled until
    // that nested promise has completed and the click handlers are bound.
    const nestedReady=window.GP_CONTROLLER_READY;
    if(!nestedReady || nestedReady===bootstrapPromise){
      throw new Error('Nested controller readiness promise missing');
    }
    await nestedReady;

    const searchButton=document.getElementById('search-button');
    if(!searchButton) throw new Error('Search button missing');

    window.GP_CONTROLLER_IDENTITY={
      version:I.version,
      buildId:I.buildId,
      apiContract:I.apiContract,
      module:'controller-0431.js',
      nestedControllerReady:true,
      searchButtonFound:true
    };
    window.dispatchEvent(new CustomEvent('gp-controller-ready',{detail:window.GP_CONTROLLER_IDENTITY}));
    return true;
  })();

  window.GP_CONTROLLER_READY=bootstrapPromise;
})();
