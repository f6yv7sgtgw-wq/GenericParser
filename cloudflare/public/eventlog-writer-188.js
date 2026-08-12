/* GenericParser 1.8.8 - der fehlende Schreiber des Eventlogs.
 *
 * Bis 1.8.7 pruefte jeder Aufrufer nur `typeof window.gpEventLog === 'function'`
 * und die Log-Seite las einen Speicher, den niemand fuellte. Alle Aufrufe waren
 * damit wirkungslos und das Log blieb dauerhaft leer.
 */
(() => {
  'use strict';

  const FALLBACK_KEY = 'generic-parser-eventlog';
  const MAX_ENTRIES = 800;

  const logKey = () => window.GP_BUILD_IDENTITY?.eventLogKey || FALLBACK_KEY;

  function read() {
    try {
      const raw = JSON.parse(localStorage.getItem(logKey()) || '[]');
      return Array.isArray(raw) ? raw : [];
    } catch {
      return [];
    }
  }

  function write(entries) {
    try {
      localStorage.setItem(logKey(), JSON.stringify(entries));
      return true;
    } catch {
      // Voller Speicher darf eine laufende Suche nicht abbrechen. Lieber die
      // aeltere Haelfte opfern als das Log ganz verlieren.
      try {
        localStorage.setItem(logKey(), JSON.stringify(entries.slice(-Math.ceil(MAX_ENTRIES / 4))));
        return true;
      } catch {
        return false;
      }
    }
  }

  function append(type, message, data) {
    const entry = {
      at: new Date().toISOString(),
      type: String(type || 'event'),
      message: String(message || ''),
      version: window.GP_BUILD_IDENTITY?.version || null
    };
    if (data && typeof data === 'object') {
      try {
        // Nur serialisierbare Nutzlast: ein zyklisches Objekt wuerde sonst den
        // gesamten Schreibvorgang scheitern lassen.
        entry.data = JSON.parse(JSON.stringify(data));
      } catch {
        entry.data = {unserializable: true};
      }
    }
    const entries = read();
    entries.push(entry);
    write(entries.slice(-MAX_ENTRIES));
    return entry;
  }

  // Einen bereits vorhandenen Schreiber nicht verdraengen.
  if (typeof window.gpEventLog !== 'function') {
    window.gpEventLog = append;
  }
  window.GPEventLogWriter = {append, read, logKey, MAX_ENTRIES};
})();
