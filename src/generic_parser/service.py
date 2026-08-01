from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol, runtime_checkable

from .models import Listing, SearchProfile


@runtime_checkable
class ListingSource(Protocol):
    """Schmale Schnittstelle für einen konkreten Marktplatz-Adapter."""

    def search(self, profile: SearchProfile) -> Iterable[Listing]:
        """Liefert normalisierte Anzeigen für ein Suchprofil."""


@dataclass(slots=True)
class GenericParser:
    """Öffentliche Serviceklasse für eingebettete Nutzung.

    Version 0.1 definiert die Integrationsgrenze. Der produktive
    Kleinanzeigen-Adapter wird in Version 0.2 implementiert.
    """

    source: ListingSource

    def __post_init__(self) -> None:
        if not isinstance(self.source, ListingSource):
            raise TypeError("source muss das ListingSource-Protokoll erfüllen")

    def search(self, profile: SearchProfile) -> tuple[Listing, ...]:
        if not isinstance(profile, SearchProfile):
            raise TypeError("profile muss ein SearchProfile sein")
        listings = tuple(self.source.search(profile))
        seen: set[str] = set()
        deduplicated: list[Listing] = []
        for listing in listings:
            if not isinstance(listing, Listing):
                raise TypeError("Der Quellenadapter darf nur Listing-Objekte liefern")
            if listing.id in seen:
                continue
            seen.add(listing.id)
            deduplicated.append(listing)
        return tuple(deduplicated)
