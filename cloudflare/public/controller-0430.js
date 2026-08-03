(() => {
  'use strict';
  const I=window.GP_BUILD_IDENTITY;if(!I)throw new Error('Shared build identity missing');
  let cursorUrl=null;
  const nativeFetch=window.fetch.bind(window);
  window.fetch=async(input,init={})=>{
    const url=typeof input==='string'?input:input?.url||'';
    if(url.includes('/api/search')&&init?.body){
      try{const body=JSON.parse(init.body);if(cursorUrl)body.cursor_url=cursorUrl;init={...init,body:JSON.stringify(body)};}catch{}
    }
    const response=await nativeFetch(input,init);
    if(url.includes('/api/search')){
      try{const data=await response.clone().json();if(data?.pagination?.cursor_url)cursorUrl=data.pagination.cursor_url;if(data?.pagination?.complete)cursorUrl=null;}catch{}
    }
    return response;
  };
  const SOURCE='./controller-0411.js?v=0.430-source';
  window.GP_CONTROLLER_READY=nativeFetch(new URL(SOURCE,window.location.href),{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`Controller-Quelle HTTP ${r.status}`);return r.text();}).then(source=>{
    const replacements=[["const VERSION = '0.41.1';",`const VERSION = '${I.version}';`],["const BUILD_ID = 'gp-0411-20260802-1';",`const BUILD_ID = '${I.buildId}';`],["const LOG_KEY = 'generic-parser-eventlog-0411';",`const LOG_KEY = '${I.eventLogKey}';`]];
    for(const[from,to]of replacements){if(!source.includes(from))throw new Error(`Controller-Konstante fehlt: ${from}`);source=source.replace(from,to);}
    Function(`${source}\n//# sourceURL=controller-0430-runtime.js`)();
    const delay=document.getElementById('page-delay');if(delay){delay.value='5000';delay.disabled=true;}
    window.GP_CONTROLLER_VERSION=I.version;window.dispatchEvent(new CustomEvent('gp-controller-ready',{detail:I}));return true;
  });
})();
