(() => {
  'use strict';
  const I = window.GP_BUILD_IDENTITY;
  if (!I) throw new Error('Build identity missing');
  const sourceUrl = new URL('./auto-resume-04462.js?v=0.4466-clean-rollback-source', location.href);
  fetch(sourceUrl, {cache:'no-store'})
    .then(response => { if (!response.ok) throw new Error(`Auto-resume source HTTP ${response.status}`); return response.text(); })
    .then(source => {
      const from = "const RECOVERY_KEY = 'generic-parser-auto-resume-04462';";
      const to = "const RECOVERY_KEY = 'generic-parser-auto-resume-04466';";
      if (!source.includes(from)) throw new Error('0.44.6.2 recovery key fragment missing');
      source = source.replace(from, to);
      Function(`${source}\n//# sourceURL=auto-resume-04466-runtime.js`)();
    })
    .catch(error => {
      if (typeof window.gpEventLog === 'function') {
        window.gpEventLog('auto_resume_loader_error', '0.44.6.2-Recovery konnte nicht geladen werden', {detail:String(error?.message || error),buildId:I.buildId});
      }
    });
})();
