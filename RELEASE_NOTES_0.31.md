# GenericParser 0.31

- stabiler API-Vertrag für Matchdaten (`match-v1`)
- Matchdaten werden gebündelt und abwärtskompatibel auf oberster Ebene geliefert
- Frontend akzeptiert beide Formen und zeigt keine `undefined`-Werte mehr
- API-Antworten werden vor dem Rendern validiert
- Score, Entscheidung, Trefferklasse, Gründe und Warnungen haben sichere Fallbacks
- Version und Service-Worker-Cache auf 0.31 angehoben
- End-to-End-Regressionsprüfung für den Matchvertrag ergänzt
- Validierung: 82 Tests bestanden, 1 optionaler Live-Test übersprungen
