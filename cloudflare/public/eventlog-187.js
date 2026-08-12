/* GenericParser 1.8.7 - Log als Datei herunterladen.
 *
 * "Log kopieren" reicht nicht, wenn ein Lauf über hunderte Einträge geht oder
 * das Ergebnis weitergegeben werden soll. Der Export trägt die Release-Identität
 * mit, damit ein später gelesenes Log einem Stand zuzuordnen ist.
 */
(() => {
  'use strict';

  const FALLBACK_KEY = 'generic-parser-eventlog';

  function logKey() {
    return window.GP_BUILD_IDENTITY?.eventLogKey || FALLBACK_KEY;
  }

  function entries() {
    try {
      const raw = JSON.parse(localStorage.getItem(logKey()) || '[]');
      return Array.isArray(raw) ? raw : [];
    } catch {
      return [];
    }
  }

  function exportPayload(now) {
    const identity = window.GP_BUILD_IDENTITY || {};
    const rows = entries();
    return {
      product: 'GenericParser',
      version: identity.version || null,
      build_id: identity.buildId || null,
      identity_source: identity.identitySource || null,
      exported_at: now,
      entry_count: rows.length,
      entries: rows
    };
  }

  function fileName(now) {
    const identity = window.GP_BUILD_IDENTITY || {};
    // Doppelpunkte aus der Zeitangabe sind in Dateinamen unter Windows verboten.
    const stamp = String(now).replace(/[:.]/g, '-');
    return `genericparser-log-${identity.version || 'unknown'}-${stamp}.json`;
  }

  function download(button) {
    const now = new Date().toISOString();
    const payload = exportPayload(now);
    if (!payload.entry_count) {
      if (button) button.textContent = 'Log ist leer';
      return false;
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = fileName(now);
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    // Ohne Freigabe bleibt der Blob für die Lebensdauer des Dokuments im Speicher.
    setTimeout(() => URL.revokeObjectURL(url), 0);
    if (button) button.textContent = `${payload.entry_count} Einträge gespeichert`;
    return true;
  }

  function install() {
    const button = document.getElementById('download-log');
    if (!button) return;
    button.addEventListener('click', event => {
      const target = event.currentTarget;
      try {
        download(target);
      } catch {
        target.textContent = 'Download nicht möglich';
      }
      setTimeout(() => { target.textContent = 'Log herunterladen'; }, 1600);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }

  window.GPEventLogExport = {entries, exportPayload, fileName, download};
})();
