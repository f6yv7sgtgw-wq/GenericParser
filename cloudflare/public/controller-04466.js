(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');
  window.GP_HANDSHAKE_READY = true;
  const sourceUrl = new URL('./controller-0411.js?v=0.4466-reference-source', location.href);
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

      const declarationAnchor = '  let requestSequence = 0;';
      const declarationPatch = `  let requestSequence = 0;\n  const TEST_COOLDOWN_THRESHOLD = Number(I.testCooldown?.threshold || 120);\n  const TEST_COOLDOWN_MS = Number(I.testCooldown?.durationMs || 90000);\n  let testCooldownSessionId = '';\n  let testCooldownPending = false;\n  let testCooldownDone = false;\n  const testCooldownSeen = new Set();`;
      if (!source.includes(declarationAnchor)) throw new Error('Cooldown declaration anchor missing');
      source = source.replace(declarationAnchor, declarationPatch);

      const beforeFetchAnchor = "    log('before_fetch', 'Vor Netzwerkaufruf', {...common, payload});";
      const beforeFetchPatch = `    if (testCooldownSessionId !== activeSessionId) {\n      testCooldownSessionId = activeSessionId;\n      testCooldownPending = false;\n      testCooldownDone = false;\n      testCooldownSeen.clear();\n    }\n\n    if (testCooldownPending && !testCooldownDone) {\n      testCooldownPending = false;\n      testCooldownDone = true;\n      const cooldownStartedAt = Date.now();\n      log('cooldown_start', 'Geplante 90-Sekunden-Testpause gestartet', {...common,threshold:TEST_COOLDOWN_THRESHOLD,uniqueResults:testCooldownSeen.size,durationMs:TEST_COOLDOWN_MS,mode:'client_request_gate'});\n      const cooldownMessage = document.getElementById('message');\n      if (cooldownMessage) {\n        cooldownMessage.className = 'message';\n        cooldownMessage.textContent = 'Testpause aktiv: Der Worker erhält 90 Sekunden lang keinen neuen Suchauftrag.';\n      }\n      while (!stopRequested) {\n        const remaining = Math.max(0, TEST_COOLDOWN_MS - (Date.now() - cooldownStartedAt));\n        if (!remaining) break;\n        workerState('Geplante Testpause', \`${'${'}testCooldownSeen.size} Treffer erreicht · Fortsetzung in ${'${'}Math.ceil(remaining / 1000)} Sekunden\`, 'working');\n        await new Promise(resolve => setTimeout(resolve, Math.min(1000, remaining)));\n      }\n      if (stopRequested) {\n        log('cooldown_cancelled', 'Geplante Testpause durch Suchstopp beendet', {...common,threshold:TEST_COOLDOWN_THRESHOLD,uniqueResults:testCooldownSeen.size});\n      } else {\n        log('cooldown_resume', 'Suche nach geplanter 90-Sekunden-Testpause fortgesetzt', {...common,threshold:TEST_COOLDOWN_THRESHOLD,uniqueResults:testCooldownSeen.size,durationMs:TEST_COOLDOWN_MS});\n        workerState('Suche wird fortgesetzt', \`${'${'}testCooldownSeen.size} Treffer · nächstes Arbeitspaket startet\`, 'working');\n        if (cooldownMessage) cooldownMessage.className = 'message hidden';\n      }\n    }\n\n${beforeFetchAnchor}`;
      if (!source.includes(beforeFetchAnchor)) throw new Error('Cooldown before-fetch anchor missing');
      source = source.replace(beforeFetchAnchor, beforeFetchPatch);

      const afterParseAnchor = "      if (!contentType.includes('application/json') && /Error\\s*1101|Worker threw exception/i.test(text)) {";
      const afterParsePatch = `      if (response.ok && Array.isArray(parsed?.listings)) {\n        for (const listing of parsed.listings) {\n          const fallback = \`${'${'}String(listing?.title || '')}|${'${'}String(listing?.price ?? '')}\`;\n          const key = String(listing?.id ?? listing?.listing_id ?? listing?.ad_id ?? listing?.url ?? fallback);\n          if (key) testCooldownSeen.add(key);\n        }\n        if (!testCooldownDone && !testCooldownPending && testCooldownSeen.size >= TEST_COOLDOWN_THRESHOLD) {\n          testCooldownPending = true;\n          log('cooldown_threshold_reached', 'Schwelle für geplante Testpause erreicht', {...common,threshold:TEST_COOLDOWN_THRESHOLD,uniqueResults:testCooldownSeen.size,durationMs:TEST_COOLDOWN_MS});\n        }\n      }\n\n${afterParseAnchor}`;
      if (!source.includes(afterParseAnchor)) throw new Error('Cooldown after-parse anchor missing');
      source = source.replace(afterParseAnchor, afterParsePatch);

      Function(`${source}\n//# sourceURL=controller-04466-runtime.js`)();
      const button = document.getElementById('search-button');
      if (button) { button.disabled = false; button.textContent = 'Live-Suche starten'; }
      const connection = document.getElementById('connection');
      if (connection) { connection.classList.remove('offline'); connection.innerHTML = '<span></span> Bereit'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className = 'compact-status done'; state.innerHTML = '<strong>Bereit</strong><span>Testversion · einmal 90 Sekunden Pause nach 120 Treffern</span>'; }
      const toggle = document.getElementById('technical-toggle');
      const technical = document.getElementById('technical-content');
      if (toggle && technical) toggle.onclick = () => { const open = technical.classList.toggle('open'); toggle.setAttribute('aria-expanded', String(open)); toggle.textContent = open ? 'Technische Details schließen' : 'Technische Details anzeigen'; };
      window.GP_CONTROLLER_IDENTITY = {version:I.version,buildId:I.buildId,apiContract:I.apiContract,module:'controller-04466.js',referenceVersion:'0.44.4',operationalReference:'0.44.6.5',runtimeReference:'0.44.6.2',searchCoreChanged:false,autoResume:true,testCooldown:true,cooldownThreshold:120,cooldownDurationMs:90000};
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
