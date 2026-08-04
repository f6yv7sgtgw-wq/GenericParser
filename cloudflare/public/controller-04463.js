(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');
  window.GP_HANDSHAKE_READY = true;
  const sourceUrl = new URL('./controller-0411.js?v=0.4463-b2-reference-source', location.href);
  fetch(sourceUrl, {cache: 'no-store'})
    .then(response => { if (!response.ok) throw new Error(`Controller source HTTP ${response.status}`); return response.text(); })
    .then(source => {
      const replacements = [
        ["const VERSION = '0.41.1';", `const VERSION = '${I.version}';`],
        ["const BUILD_ID = 'gp-0411-20260802-1';", `const BUILD_ID = '${I.buildId}';`],
        ["const API_CONTRACT = 'match-v6.1-page-worker';", `const API_CONTRACT = '${I.apiContract}';`],
        ["const LOG_KEY = 'generic-parser-eventlog-0411';", `const LOG_KEY = '${I.eventLogKey}';`],
        [
          "const workerPhase = response.headers.get('X-GenericParser-Phase') || null;\n      log('after_fetch', 'Netzwerkantwort erhalten', {...common,status:response.status,ok:response.ok,elapsedMs,contentType,contentLengthHeader,workerVersion,workerBuild,workerContract,phase:workerPhase});",
          "const workerPhase = response.headers.get('X-GenericParser-Phase') || null;\n      const cfErrorType = response.headers.get('cf-error-type') || null;\n      const cfErrorOrigin = response.headers.get('cf-error-origin') || null;\n      const retryAfter = response.headers.get('retry-after') || null;\n      const responseRayId = response.headers.get('cf-ray') || null;\n      log('after_fetch', 'Netzwerkantwort erhalten', {...common,status:response.status,ok:response.ok,elapsedMs,contentType,contentLengthHeader,workerVersion,workerBuild,workerContract,phase:workerPhase,cfErrorType,cfErrorOrigin,retryAfter,responseRayId});"
        ],
        [
          "log('worker_1101', 'Cloudflare Worker-Ausnahme vor ASGI', {...common,status:response.status,elapsedMs,responseBytes,phase:'runtime_before_asgi',rayId});",
          "log('worker_1101', 'Cloudflare Worker-Ausnahme vor ASGI', {...common,status:response.status,elapsedMs,responseBytes,phase:'runtime_before_asgi',rayId,cfErrorType:cfErrorType||'1101',cfErrorOrigin,retryAfter,responseRayId});"
        ]
      ];
      for (const [from, to] of replacements) {
        if (!source.includes(from)) throw new Error(`Controller source fragment missing: ${from.slice(0,80)}`);
        source = source.replace(from, to);
      }
      Function(`${source}\n//# sourceURL=controller-04463-runtime-b2.js`)();

      const recoveryKey = String(I.autoResume?.recoveryKey || 'generic-parser-auto-resume-04463');
      let lastUnlockSignature = '';
      const syncResumeControl = () => {
        let recovery = null;
        try { recovery = JSON.parse(localStorage.getItem(recoveryKey) || 'null'); } catch {}
        const resume = document.getElementById('resume-button');
        if (!resume) return;
        const resumable = recovery && ['waiting', 'probing', 'starting_auto', 'manual_required'].includes(recovery.status);
        if (resumable) {
          resume.classList.remove('hidden');
          if (window.GP_HANDSHAKE_READY === true) resume.disabled = false;
          const signature = `${recovery.status}:${recovery.failureSignature || ''}:${recovery.results || 0}`;
          if (signature !== lastUnlockSignature && typeof window.gpEventLog === 'function') {
            lastUnlockSignature = signature;
            window.gpEventLog('resume_control_ready', 'Fortsetzen-Schaltfläche nach Recovery-Unterbrechung freigegeben', {
              recoveryStatus: recovery.status,
              failureSignature: recovery.failureSignature || null,
              results: Number(recovery.results || 0),
              buildId: I.buildId,
            });
          }
          return;
        }
        if (recovery && ['running', 'auto_running', 'completed', 'cancelled', 'cleared'].includes(recovery.status)) {
          resume.disabled = true;
          resume.classList.add('hidden');
        }
      };
      syncResumeControl();
      window.addEventListener('storage', syncResumeControl);
      setInterval(syncResumeControl, 500);

      const button = document.getElementById('search-button');
      if (button) { button.disabled = false; button.textContent = 'Live-Suche starten'; }
      const connection = document.getElementById('connection');
      if (connection) { connection.classList.remove('offline'); connection.innerHTML = '<span></span> Bereit'; }
      const state = document.getElementById('worker-state-text');
      if (state) { state.className = 'compact-status done'; state.innerHTML = '<strong>Bereit</strong><span>Referenz 0.44.4 · Recovery-Hardening mit Resume-Hotfix aktiv</span>'; }
      const toggle = document.getElementById('technical-toggle');
      const technical = document.getElementById('technical-content');
      if (toggle && technical) toggle.onclick = () => { const open = technical.classList.toggle('open'); toggle.setAttribute('aria-expanded', String(open)); toggle.textContent = open ? 'Technische Details schließen' : 'Technische Details anzeigen'; };
      window.GP_CONTROLLER_IDENTITY = {version:I.version,buildId:I.buildId,apiContract:I.apiContract,module:'controller-04463.js',referenceVersion:'0.44.4',searchCoreChanged:false,autoResume:true,maxAutoResumes:2,recoveryProbe:true,resumeControlHotfix:true};
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
