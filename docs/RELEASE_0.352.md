# GenericParser 0.352

## Ziel

Version 0.352 stellt einen konsistenten Datenfluss zwischen Browser, Worker, Kleinanzeigen-Abruf, Matching und Darstellung her.

## Änderungen

- Mobile-API und HTML-Fallback verwenden dieselbe mehrseitige Sammellogik.
- Ergebnisse werden seitenübergreifend anhand der Anzeigen-ID dedupliziert.
- Ein Ergebnislimit wirkt ausschließlich nach bewusster Benutzereingabe.
- Standardmäßig werden Treffer, Prüffälle und abgelehnte Anzeigen angezeigt; Matching klassifiziert, blendet aber nicht mehr still aus.
- Die API weist `fetched_listings`, `scored_listings` und `visible_listings` getrennt aus.
- Pagination zeigt Quelle, Seitengröße, Seitenanzahl, Seitenfunde, neue IDs, Duplikate, Fallback-Grund und Stop-Grund.
- Der HTML-Fallback ist nicht mehr auf die erste Ergebnisseite beschränkt.
- Die Sicherheitsgrenze bleibt bei 100 Seiten, um Endlosschleifen zu verhindern.

## Datenvertrag

Ohne explizites Benutzerlimit endet ein Abruf nur bei einem echten Seitenende, einer wiederholten Seite, einer Seite ohne neue IDs oder dem Sicherheitslimit. `max_results` wird nur angewendet, wenn `max_results_explicit=true` gesetzt ist.
