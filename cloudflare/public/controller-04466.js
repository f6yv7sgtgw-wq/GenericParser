(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');
  window.GP_HANDSHAKE_READY = true;
  const sourceUrl = new URL('./controller-0411.js?v=0.4466b2-reference-source', location.href);
  fetch(sourceUrl, {cache: 'no-store'})
    .then(response => { if (!response.ok) throw new Error(`Controller source HTTP ${response.status}`); return response.text(); })
    .then(source => {
      const replacements = [
        ["const VERSION = '0.41.1';", `const VERSION = '${I.version}';`],
        ["const BUILD_ID = 'gp-0411-20260802-1';", `const BUILD_ID = '${I.buildId}';`],
        ["const API_CONTRACT = 'match-v6.1-page-worker';", `const API_CONTRACT = '${I.apiContract}';`],
        ["const LOG_KEY = 'generic-parser-eventlog-0411';", `const LOG_KEY = '${I.eventLogKey}';`]
      ];
      for (const [from, to] of replacements) {
        if (!source.includes(from)) throw new Error(`Controller constant missing: ${from}`);
        source = source.replace(from, to);
      }

      const countdownAnchor = "async function countdown(ms,page,loaded,label='Nächste Seite'){const start=Date.now();while(!stopRequested){const rest=ms-(Date.now()-start);if(rest<=0)break;workerState('Worker wartet',`${label} ${page+1} in ${(rest/1000).toFixed(1).replace('.',',')} s · ${loaded} Ergebnisse gespeichert`,'working');await sleep(Math.min(200,rest));}}";
      const countdownPatch = [
        "const TEST_COOLDOWN_STEP = 120;",
        "const TEST_COOLDOWN_MS = 90000;",
        "const TEST_COOLDOWN_KEY = 'generic-parser-cooldown-04466-b2';",
        "function readTestCooldown(){try{const value=JSON.parse(localStorage.getItem(TEST_COOLDOWN_KEY)||'null');return value&&typeof value==='object'?value:null;}catch{return null;}}",
        "function writeTestCooldown(value){try{localStorage.setItem(TEST_COOLDOWN_KEY,JSON.stringify(value));}catch{}}",
        "function testCooldownState(loaded){",
        "  const signatureValue=String(activeState?.signature||activeQuery||'');",
        "  let state=readTestCooldown();",
        "  const previous=Number(state?.lastObserved||0);",
        "  if(!state||state.signature!==signatureValue||loaded<previous){",
        "    state={signature:signatureValue,nextThreshold:TEST_COOLDOWN_STEP,lastObserved:loaded,completedThresholds:[]};",
        "  }",
        "  state.lastObserved=loaded;",
        "  if(!Array.isArray(state.completedThresholds))state.completedThresholds=[];",
        "  return state;",
        "}",
        "async function countdown(ms,page,loaded,label='Nächste Seite'){",
        "  let threshold=null;",
        "  if(label==='Nächste Seite'){",
        "    const state=testCooldownState(Number(loaded||0));",
        "    if(Number(loaded||0)>=Number(state.nextThreshold||TEST_COOLDOWN_STEP)){",
        "      threshold=Number(state.nextThreshold||TEST_COOLDOWN_STEP);",
        "      while(Number(loaded||0)>=Number(state.nextThreshold||TEST_COOLDOWN_STEP))state.nextThreshold=Number(state.nextThreshold||TEST_COOLDOWN_STEP)+TEST_COOLDOWN_STEP;",
        "      state.completedThresholds.push(threshold);",
        "      writeTestCooldown(state);",
        "      ms=TEST_COOLDOWN_MS;",
        "      log('cooldown_threshold_reached','Schwelle für wiederholte Testpause erreicht',{sessionId:activeSessionId,query:activeQuery,threshold,uniqueResults:Number(loaded||0),nextThreshold:state.nextThreshold,durationMs:TEST_COOLDOWN_MS,mode:'replace_regular_delay'});",
        "      log('cooldown_start','90-Sekunden-Testpause gestartet',{sessionId:activeSessionId,query:activeQuery,threshold,uniqueResults:Number(loaded||0),nextThreshold:state.nextThreshold,durationMs:TEST_COOLDOWN_MS,mode:'replace_regular_delay'});",
        "    }else{writeTestCooldown(state);}",
        "  }",
        "  const start=Date.now();",
        "  while(!stopRequested){",
        "    const rest=ms-(Date.now()-start);",
        "    if(rest<=0)break;",
        "    if(threshold!==null){",
        "      workerState('Geplante Testpause','Schwelle '+threshold+' erreicht · Fortsetzung in '+Math.ceil(rest/1000)+' Sekunden · '+loaded+' Ergebnisse gespeichert','working');",
        "    }else{",
        "      workerState('Worker wartet',label+' '+(page+1)+' in '+(rest/1000).toFixed(1).replace('.',',')+' s · '+loaded+' Ergebnisse gespeichert','working');",
        "    }",
        "    await sleep(Math.min(threshold!==null?1000:200,rest));",
        "  }",
        "  if(threshold!==null){",
        "    if(stopRequested){",
        "      log('cooldown_cancelled','Testpause durch Suchstopp beendet',{sessionId:activeSessionId,query:activeQuery,threshold,uniqueResults:Number(loaded||0)});",
        "    }else{",
        "      const state=readTestCooldown();",
        "      log('cooldown_resume','Suche nach 90-Sekunden-Testpause fortgesetzt',{sessionId:activeSessionId,query:activeQuery,threshold,uniqueResults:Number(loaded||0),nextThreshold:Number(state?.nextThreshold||threshold+TEST_COOLDOWN_STEP),durationMs:TEST_COOLDOWN_MS});",
        "      workerState('Suche wird fortgesetzt','Pause nach '+threshold+' Treffern beendet · nächstes Arbeitspaket startet','working');",
        "    }",
        "  }",
        "}"
      ].join('\n');
      if (!source.includes(countdownAnchor)) throw new Error('Reference countdown anchor missing');
      source = source.replace(countdownAnchor, countdownPatch);

      Function(`${source}\n//# sourceURL=controller-04466-build2-runtime.js`)();
      const button = document.getElementById('search-button');
      if (button) { button.disabled = false; button.textContent = 'Live-Suche starten'; }
      const connection = document.getElementById('connection');
      if (connection) { connection.classList.remove('offline'); connection.innerHTML = '<span></span> Bereit'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className = 'compact-status done'; state.innerHTML = '<strong>Bereit</strong><span>Testversion · 90 Sekunden Pause bei 120, 240, 360 … Treffern</span>'; }
      const toggle = document.getElementById('technical-toggle');
      const technical = document.getElementById('technical-content');
      if (toggle && technical) toggle.onclick = () => { const open = technical.classList.toggle('open'); toggle.setAttribute('aria-expanded', String(open)); toggle.textContent = open ? 'Technische Details schließen' : 'Technische Details anzeigen'; };
      window.GP_CONTROLLER_IDENTITY = {version:I.version,buildId:I.buildId,apiContract:I.apiContract,module:'controller-04466.js',referenceVersion:'0.44.4',operationalReference:'0.44.6.5',runtimeReference:'0.44.6.2',searchCoreChanged:false,autoResume:true,testCooldown:true,cooldownStep:120,cooldownDurationMs:90000,cooldownMode:'repeated-multiples'};
      window.dispatchEvent(new CustomEvent('gp-controller-ready',{detail:window.GP_CONTROLLER_IDENTITY}));
    })
    .catch(error => {
      window.GP_HANDSHAKE_READY = false;
      const button = document.getElementById('search-button');
      if (button) { button.disabled = true; button.textContent = 'Live-Suche gesperrt'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className='compact-status error'; state.textContent=`Controller konnte nicht geladen werden: ${error.message || error}`; }
    });
})();
