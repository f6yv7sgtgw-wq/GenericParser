(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');

  const sourceUrl = new URL('./auto-resume-04463.js?v=0.4464-reference-source', location.href);
  fetch(sourceUrl, {cache: 'no-store'})
    .then(response => {
      if (!response.ok) throw new Error(`Recovery source HTTP ${response.status}`);
      return response.text();
    })
    .then(source => {
      const replacements = [
        [
          "const checksOk = body?.status === 'ready' && body?.search_ready === true && body?.reference_core_loaded === true && Object.values(body?.checks || {}).every(Boolean);",
          "const checksOk = body?.status === 'ready' && body?.bootstrap_ready === true && body?.lazy_search_import === true && body?.probe_mode === 'bootstrap_lazy' && Object.values(body?.checks || {}).every(Boolean);"
        ],
        [
          "reason: response.ok ? (identityOk && checksOk ? 'Suchpfad bereit' : 'Probe unvollständig oder Identität abweichend') : `HTTP ${response.status}`",
          "reason: response.ok ? (identityOk && checksOk ? 'Worker-Bootstrap bereit' : 'Probe unvollständig oder Identität abweichend') : `HTTP ${response.status}`"
        ],
        [
          "appendLog('recovery_probe_ready', 'Vollständiger Suchpfad ist bereit', {",
          "appendLog('recovery_probe_ready', 'Worker-Bootstrap ist bereit', {"
        ],
        [
          "setStatus('Automatische Fortsetzung startet', `Versuch ${recovery.autoResumeCount}/${options.maxAutoResumes} · vollständiger Suchpfad bereit`);",
          "setStatus('Automatische Fortsetzung startet', `Versuch ${recovery.autoResumeCount}/${options.maxAutoResumes} · Worker-Bootstrap bereit`);"
        ],
        [
          "requireManual('probe_attempts_exhausted', 'Der vollständige Suchpfad wurde nach mehreren Prüfungen nicht stabil bereit.');",
          "requireManual('probe_attempts_exhausted', 'Der Worker-Bootstrap wurde nach mehreren Prüfungen nicht stabil bereit.');"
        ],
        [
          "message.textContent = 'Der Suchstand bleibt gespeichert. Nach der gestaffelten Ruhezeit wird der vollständige Suchpfad geprüft und anschließend automatisch fortgesetzt.';",
          "message.textContent = 'Der Suchstand bleibt gespeichert. Nach der gestaffelten Ruhezeit wird der leichte Worker-Bootstrap geprüft und anschließend automatisch fortgesetzt.';"
        ]
      ];

      for (const [from, to] of replacements) {
        if (!source.includes(from)) throw new Error(`Recovery source fragment missing: ${from.slice(0, 100)}`);
        source = source.replace(from, to);
      }

      source = source.replace(
        "endpoint: options.probeEndpoint,",
        "endpoint: options.probeEndpoint, probeMode: I.autoResume?.probeMode || 'bootstrap_lazy',"
      );
      source = source.replace(
        "workerBuild: probe.body?.build_id || null,",
        "workerBuild: probe.body?.build_id || null, probeMode: probe.body?.probe_mode || null, serviceLoaded: Boolean(probe.body?.service_loaded),"
      );

      Function(`${source}\n//# sourceURL=auto-resume-04464-runtime.js`)();
    })
    .catch(error => {
      const state = document.getElementById('worker-state-text');
      if (state) {
        state.className = 'compact-status error';
        state.innerHTML = `<strong>Recovery konnte nicht geladen werden</strong><span>${String(error?.message || error)}</span>`;
      }
      if (typeof window.gpEventLog === 'function') {
        window.gpEventLog('recovery_bootstrap_failed', 'Recovery-Script konnte nicht geladen werden', {
          recoveryVersion: I.version,
          buildId: I.buildId,
          error: String(error?.message || error),
        });
      }
    });
})();
