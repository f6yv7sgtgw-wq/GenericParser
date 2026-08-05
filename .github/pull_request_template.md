## Inhalt

- Was wurde geändert?
- Warum ist die Änderung erforderlich?
- Ändert sie Suchverhalten, API-Vertrag oder Plattformbedarf?

## Prüfung

- [ ] Relevante lokale Tests bestanden
- [ ] Referenzkern und Rückfallstand bleiben geschützt oder die Abweichung ist ausdrücklich beschrieben
- [ ] Debug-Logs und Selbsttests bleiben standardmäßig aus

## Bei Releasewirkung zusätzlich

- [ ] `VERSION.json`, README, Changelog, Roadmap und Release-Index aktualisiert
- [ ] vollständiger API-Snapshot `docs/API_<VERSION>.md` aktualisiert
- [ ] Release Notes `docs/releases/<VERSION>.md` aktualisiert
- [ ] Funktion und bekannte Limitierungen vollständig dokumentiert
- [ ] aktuelle Cloudflare-Free-Grenzen offiziell geprüft und datiert
- [ ] Service-Worker-Cache und aktive Identitäten konsistent
- [ ] GitHub-CI und Cloudflare-Liveprüfung vorgesehen
