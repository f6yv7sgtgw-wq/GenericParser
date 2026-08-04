(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');
  const sourceUrl = new URL('./auto-resume-04462.js?v=0.44661-recovery-source', location.href);
  fetch(sourceUrl, {cache:'no-store'})
    .then(response => { if (!response.ok) throw new Error(`Auto-resume source HTTP ${response.status}`); return response.text(); })
    .then(source => {
      const keyFrom = "const RECOVERY_KEY = 'generic-parser-auto-resume-04462';";
      const keyTo = "const RECOVERY_KEY = 'generic-parser-auto-resume-044661';";
      if (!source.includes(keyFrom)) throw new Error('0.44.6.2 recovery key fragment missing');
      source = source.replace(keyFrom, keyTo);

      const waitFrom = `  async function waitForResumeButton(timeoutMs = 10000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const button = document.getElementById('resume-button');
      if (button && !button.disabled && !button.classList.contains('hidden')) return button;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    return null;
  }`;
      const waitTo = `  async function waitForResumeButton(timeoutMs = 10000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const button = document.getElementById('resume-button');
      if (button) {
        button.classList.remove('hidden');
        button.disabled = false;
        button.textContent = 'Letzte Suche fortsetzen';
        if (!button.disabled && !button.classList.contains('hidden')) return button;
      }
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    return null;
  }`;
      if (!source.includes(waitFrom)) throw new Error('0.44.6.2 resume-control fragment missing');
      source = source.replace(waitFrom, waitTo);

      const clickFrom = '    button.click();';
      const clickTo = `    const resumeIssuedAt = Date.now();
    button.click();
    const controlRetryMs = Number(I.autoResume?.controlRetryMs || 10000);
    setTimeout(() => {
      const resumed = readEvents().some(event => event.type === 'search_resume' && eventEpoch(event) >= resumeIssuedAt);
      if (resumed || !recovery || recovery.status !== 'starting_auto') return;
      const retryButton = document.getElementById('resume-button');
      if (!retryButton) {
        requireManual('resume_control_missing_after_click', 'Die Fortsetzen-Steuerung fehlt auch nach erfolgreicher Worker-Prüfung.');
        return;
      }
      retryButton.classList.remove('hidden');
      retryButton.disabled = false;
      appendLog('auto_resume_control_retry', 'Fortsetzen-Steuerung wird ein zweites Mal ausgelöst', {
        sessionId: recovery.failureSessionId,
        results: Number(recovery.results || 0),
        retryAfterMs: controlRetryMs,
      });
      retryButton.click();
      setTimeout(() => {
        const retryResumed = readEvents().some(event => event.type === 'search_resume' && eventEpoch(event) >= resumeIssuedAt);
        if (!retryResumed && recovery?.status === 'starting_auto') {
          requireManual('resume_control_failed_after_retry', 'Die Fortsetzen-Steuerung hat nach zwei Auslösungen keine neue Suchsession gestartet.');
        }
      }, 5000);
    }, controlRetryMs);`;
      if (!source.includes(clickFrom)) throw new Error('0.44.6.2 resume click fragment missing');
      source = source.replace(clickFrom, clickTo);

      Function(`${source}\n//# sourceURL=auto-resume-044661-runtime.js`)();
    })
    .catch(error => {
      if (typeof window.gpEventLog === 'function') {
        window.gpEventLog('auto_resume_loader_error', '0.44.6.6.1-Recovery konnte nicht geladen werden', {detail:String(error?.message || error),buildId:I.buildId});
      }
    });
})();
