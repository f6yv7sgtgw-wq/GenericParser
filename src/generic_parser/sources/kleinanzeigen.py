from __future__ import annotations

import random
import re
import threading
import time
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Callable, Iterable, Mapping, Sequence
from urllib.parse import quote, urlencode, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from ..models import Listing, SearchProfile
from ..normalization import BERLIN, normalize_text, parse_location, parse_posted_at, parse_price

BASE_URL = "https://www.kleinanzeigen.de"
_LOCATION_ID_RE = re.compile(r"(?:^|[/?])k\d*(?:c\d+)?l(?P<id>\d+)(?:r\d+)?(?:[/?]|$)")
_NO_RESULTS_MARKERS = (
    "keine anzeigen gefunden",
    "keine ergebnisse gefunden",
    "leider keine treffer",
    "0 ergebnisse",
)
_BLOCK_MARKERS = (
    "captcha",
    "cf chl",
    "challenge platform",
    "access denied",
    "automatisierte anfragen",
    "ungewoehnlicher datenverkehr",
)


class KleinanzeigenError(RuntimeError):
    """Basisklasse für Kleinanzeigen-Fehler."""


class KleinanzeigenBlockedError(KleinanzeigenError):
    """Kleinanzeigen hat den Abruf geblockt oder eine Challenge geliefert."""


class KleinanzeigenLayoutError(KleinanzeigenError):
    """Die Seite ist erreichbar, aber die erwartete Ergebnisstruktur fehlt."""


class PageState(str, Enum):
    RESULTS = "results"
    NO_RESULTS = "no_results"
    BLOCKED = "blocked"
    LAYOUT_CHANGED = "layout_changed"


@dataclass(frozen=True, slots=True)
class FetchedPage:
    requested_url: str
    final_url: str
    status_code: int
    text: str


@dataclass(frozen=True, slots=True)
class CardParseError:
    index: int
    listing_id: str | None
    message: str


@dataclass(frozen=True, slots=True)
class PageDiagnostics:
    state: PageState
    requested_url: str
    final_url: str
    cards_found: int
    listings_parsed: int
    duplicates_skipped: int
    errors: tuple[CardParseError, ...] = ()


@dataclass(frozen=True, slots=True)
class ParsedPage:
    listings: tuple[Listing, ...]
    diagnostics: PageDiagnostics


def slugify_keyword(keyword: str) -> str:
    """Erzeugt einen robusten Kleinanzeigen-Slug aus einem Suchbegriff."""

    slug = normalize_text(keyword).replace(" ", "-")
    if not slug:
        raise ValueError("keyword darf nicht leer sein")
    return quote(slug, safe="-")


def extract_location_id(url: str) -> int | None:
    """Extrahiert die interne Location-ID aus einer Kleinanzeigen-URL."""

    match = _LOCATION_ID_RE.search(urlparse(url).path)
    return int(match.group("id")) if match else None


@dataclass(frozen=True, slots=True)
class KleinanzeigenUrlBuilder:
    base_url: str = BASE_URL
    sort_by_date: bool = True

    def keyword_url(self, profile: SearchProfile, query: str) -> str:
        slug = slugify_keyword(query)
        self._validate_keyword_location(profile)
        if profile.postal_code and profile.location_id:
            suffix = f"k0l{profile.location_id}"
            if profile.radius_km is not None:
                suffix += f"r{profile.radius_km}"
            path = f"/s-{profile.postal_code}/{slug}/{suffix}"
        else:
            path = f"/s-{slug}/k0"
        return self._with_sort(urljoin(self.base_url, path))

    def category_url(self, profile: SearchProfile, category_path: str) -> str:
        self._validate_category_location(profile)
        category = category_path.strip().strip("/")
        if not category:
            raise ValueError("category_path darf nicht leer sein")
        suffix = "k0"
        if profile.location_id:
            suffix += f"l{profile.location_id}"
            if profile.radius_km is not None:
                suffix += f"r{profile.radius_km}"
        return self._with_sort(urljoin(self.base_url, f"/{category}/{suffix}"))

    def urls_for(self, profile: SearchProfile) -> tuple[tuple[str, str], ...]:
        urls = [(query, self.keyword_url(profile, query)) for query in profile.search_queries]
        urls.extend(
            (f"category:{path}", self.category_url(profile, path))
            for path in profile.category_paths
        )
        return tuple(urls)

    @staticmethod
    def _validate_keyword_location(profile: SearchProfile) -> None:
        local_requested = any(
            value is not None
            for value in (profile.postal_code, profile.location_id, profile.radius_km)
        )
        if local_requested and (profile.postal_code is None or profile.location_id is None):
            raise ValueError(
                "Für eine lokale Keyword-Suche sind postal_code und die verifizierte location_id erforderlich"
            )

    @staticmethod
    def _validate_category_location(profile: SearchProfile) -> None:
        if (profile.postal_code is not None or profile.radius_km is not None) and profile.location_id is None:
            raise ValueError("Für eine lokale Kategoriesuche ist die verifizierte location_id erforderlich")

    def _with_sort(self, url: str) -> str:
        return f"{url}?{urlencode({'sortingField': 'SORTING_DATE'})}" if self.sort_by_date else url


class KleinanzeigenHttpClient:
    """Sequenzieller HTTP-Client mit Delay, Retries und Block-Backoff."""

    DEFAULT_USER_AGENTS = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.6 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    )

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout_seconds: float = 20.0,
        request_delay_range: tuple[float, float] = (2.0, 5.0),
        retry_wait_seconds: float = 2.0,
        blocked_backoff_seconds: float = 1800.0,
        max_attempts: int = 3,
        user_agents: Sequence[str] = DEFAULT_USER_AGENTS,
        sleep: Callable[[float], None] = time.sleep,
        random_uniform: Callable[[float, float], float] = random.uniform,
        random_choice: Callable[[Sequence[str]], str] = random.choice,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts muss mindestens 1 sein")
        if request_delay_range[0] < 0 or request_delay_range[1] < request_delay_range[0]:
            raise ValueError("Ungültiger request_delay_range")
        self._owns_client = client is None
        self._client = client or httpx.Client(follow_redirects=True, timeout=timeout_seconds)
        self._request_delay_range = request_delay_range
        self._retry_wait_seconds = retry_wait_seconds
        self._blocked_backoff_seconds = blocked_backoff_seconds
        self._max_attempts = max_attempts
        self._user_agents = tuple(user_agents)
        self._sleep = sleep
        self._random_uniform = random_uniform
        self._random_choice = random_choice
        self._lock = threading.Lock()
        self._has_requested = False

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> KleinanzeigenHttpClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get(self, url: str) -> FetchedPage:
        with self._lock:
            if self._has_requested:
                self._sleep(self._random_uniform(*self._request_delay_range))
            self._has_requested = True

            last_error: Exception | None = None
            for attempt in range(self._max_attempts):
                try:
                    response = self._client.get(url, headers=self._headers())
                except httpx.RequestError as exc:
                    last_error = exc
                    if attempt + 1 >= self._max_attempts:
                        raise KleinanzeigenError(f"Abruf fehlgeschlagen: {url}") from exc
                    self._sleep(self._retry_wait_seconds * (2**attempt))
                    continue

                page = FetchedPage(
                    requested_url=url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    text=response.text,
                )
                if response.status_code in {403, 429} or self._looks_blocked(response.text):
                    if attempt + 1 >= self._max_attempts:
                        raise KleinanzeigenBlockedError(
                            f"Kleinanzeigen blockiert den Abruf ({response.status_code})"
                        )
                    self._sleep(self._blocked_backoff_seconds * (2**attempt))
                    continue
                if response.status_code in {500, 502, 503, 504}:
                    if attempt + 1 >= self._max_attempts:
                        response.raise_for_status()
                    self._sleep(self._retry_wait_seconds * (2**attempt))
                    continue
                response.raise_for_status()
                return page

            raise KleinanzeigenError(f"Abruf fehlgeschlagen: {url}") from last_error

    def _headers(self) -> Mapping[str, str]:
        return {
            "User-Agent": self._random_choice(self._user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
            "Cache-Control": "no-cache",
        }

    @staticmethod
    def _looks_blocked(html: str) -> bool:
        normalized = normalize_text(html)
        return any(marker in normalized for marker in _BLOCK_MARKERS)


class KleinanzeigenPageParser:
    """Parst eine Kleinanzeigen-Ergebnisliste in normalisierte Listings."""

    def __init__(self, *, base_url: str = BASE_URL) -> None:
        self.base_url = base_url

    def parse(
        self,
        page: FetchedPage,
        *,
        source_query: str,
        now: datetime | None = None,
    ) -> ParsedPage:
        if page.status_code in {403, 429} or KleinanzeigenHttpClient._looks_blocked(page.text):
            raise KleinanzeigenBlockedError("Geblockte oder Challenge-Seite erkannt")

        soup = BeautifulSoup(page.text, "html.parser")
        cards = soup.select("article.aditem")
        if not cards:
            state = self._empty_state(soup.get_text(" ", strip=True))
            diagnostics = PageDiagnostics(
                state=state,
                requested_url=page.requested_url,
                final_url=page.final_url,
                cards_found=0,
                listings_parsed=0,
                duplicates_skipped=0,
            )
            if state is PageState.LAYOUT_CHANGED:
                raise KleinanzeigenLayoutError("Keine Ergebniskarten und kein Nulltreffer-Hinweis")
            return ParsedPage(listings=(), diagnostics=diagnostics)

        reference = now or datetime.now(BERLIN)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=BERLIN)
        else:
            reference = reference.astimezone(BERLIN)

        seen: set[str] = set()
        listings: list[Listing] = []
        errors: list[CardParseError] = []
        duplicates = 0
        for index, card in enumerate(cards):
            listing_id = card.get("data-adid")
            try:
                listing = self._parse_card(card, source_query=source_query, now=reference)
            except (TypeError, ValueError, AttributeError) as exc:
                errors.append(CardParseError(index=index, listing_id=listing_id, message=str(exc)))
                continue
            if listing.id in seen:
                duplicates += 1
                continue
            seen.add(listing.id)
            listings.append(listing)

        if cards and not listings:
            raise KleinanzeigenLayoutError("Alle Ergebniskarten konnten nicht geparst werden")
        diagnostics = PageDiagnostics(
            state=PageState.RESULTS,
            requested_url=page.requested_url,
            final_url=page.final_url,
            cards_found=len(cards),
            listings_parsed=len(listings),
            duplicates_skipped=duplicates,
            errors=tuple(errors),
        )
        return ParsedPage(listings=tuple(listings), diagnostics=diagnostics)

    def _parse_card(self, card: Tag, *, source_query: str, now: datetime) -> Listing:
        listing_id = (card.get("data-adid") or "").strip()
        if not listing_id:
            raise ValueError("data-adid fehlt")

        link = card.select_one("a.ellipsis[href]") or card.select_one('a[href*="/s-anzeige/"]')
        if not isinstance(link, Tag):
            raise ValueError("Titel-Link fehlt")
        title = link.get_text(" ", strip=True)
        href = link.get("href")
        if not title or not isinstance(href, str):
            raise ValueError("Titel oder Link ist leer")

        price_node = card.select_one("p.aditem-main--middle--price-shipping--price")
        location_node = card.select_one("div.aditem-main--top--left")
        date_node = card.select_one("div.aditem-main--top--right")
        description_node = card.select_one("p.aditem-main--middle--description")
        tags = tuple(
            tag.get_text(" ", strip=True)
            for tag in card.select("span.simpletag")
            if tag.get_text(" ", strip=True)
        )
        image = card.select_one("img")
        image_url: str | None = None
        if isinstance(image, Tag):
            candidate = image.get("src") or image.get("data-src") or image.get("data-imgsrc")
            if isinstance(candidate, str) and candidate.strip():
                image_url = urljoin(self.base_url, candidate.strip())

        price_raw = price_node.get_text(" ", strip=True) if price_node else ""
        location_raw = location_node.get_text(" ", strip=True) if location_node else ""
        date_raw = date_node.get_text(" ", strip=True) if date_node else ""
        description = description_node.get_text(" ", strip=True) if description_node else None

        return Listing(
            id=listing_id,
            title=title,
            url=urljoin(self.base_url, href),
            price=parse_price(price_raw),
            location=parse_location(location_raw),
            posted_at=parse_posted_at(date_raw, now=now) if date_raw else None,
            description=description or None,
            source_query=source_query,
            first_seen=now,
            last_seen=now,
            tags=tags,
            image_url=image_url,
        )

    @staticmethod
    def _empty_state(page_text: str) -> PageState:
        normalized = normalize_text(page_text)
        if any(marker in normalized for marker in _BLOCK_MARKERS):
            return PageState.BLOCKED
        if any(marker in normalized for marker in _NO_RESULTS_MARKERS):
            return PageState.NO_RESULTS
        return PageState.LAYOUT_CHANGED


@dataclass(frozen=True, slots=True)
class LocationVerification:
    local_cards: int
    nationwide_cards: int
    radius_effective: bool
    local_url: str
    nationwide_url: str


@dataclass(slots=True)
class KleinanzeigenAdapter:
    """Produktiver Listenadapter für Version 0.2a."""

    http: KleinanzeigenHttpClient
    parser: KleinanzeigenPageParser = field(default_factory=KleinanzeigenPageParser)
    urls: KleinanzeigenUrlBuilder = field(default_factory=KleinanzeigenUrlBuilder)
    now_provider: Callable[[], datetime] = lambda: datetime.now(BERLIN)
    last_diagnostics: tuple[PageDiagnostics, ...] = field(init=False, default=())

    def search(self, profile: SearchProfile) -> Iterable[Listing]:
        all_listings: list[Listing] = []
        diagnostics: list[PageDiagnostics] = []
        seen: set[str] = set()
        now = self.now_provider()
        for source_query, url in self.urls.urls_for(profile):
            fetched = self.http.get(url)
            parsed = self.parser.parse(fetched, source_query=source_query, now=now)
            diagnostics.append(parsed.diagnostics)
            for listing in parsed.listings:
                if listing.id in seen:
                    continue
                seen.add(listing.id)
                all_listings.append(listing)
        self.last_diagnostics = tuple(diagnostics)
        return tuple(all_listings)

    def verify_location_id(
        self,
        profile: SearchProfile,
        *,
        query: str | None = None,
        test_radius_km: int = 5,
    ) -> LocationVerification:
        """Vergleicht eine kleine Radius-Suche mit derselben bundesweiten Suche.

        Gleiche Kartenanzahlen gelten bewusst nicht als Nachweis einer wirksamen
        Location-ID. Für eine belastbare Prüfung sollte ein ausreichend breiter
        Suchbegriff verwendet werden.
        """

        if profile.location_id is None or profile.postal_code is None:
            raise ValueError("postal_code und location_id sind für die Verifikation erforderlich")
        selected_query = query or (profile.search_queries[0] if profile.search_queries else None)
        if not selected_query:
            raise ValueError("Für die Location-Verifikation ist eine search_query erforderlich")

        local_profile = replace(
            profile,
            search_queries=(selected_query,),
            category_paths=(),
            radius_km=test_radius_km,
        )
        nationwide_profile = replace(
            profile,
            search_queries=(selected_query,),
            category_paths=(),
            postal_code=None,
            location_id=None,
            radius_km=None,
        )
        local_url = self.urls.keyword_url(local_profile, selected_query)
        nationwide_url = self.urls.keyword_url(nationwide_profile, selected_query)
        now = self.now_provider()
        local_page = self.parser.parse(
            self.http.get(local_url), source_query=selected_query, now=now
        )
        nationwide_page = self.parser.parse(
            self.http.get(nationwide_url), source_query=selected_query, now=now
        )
        return LocationVerification(
            local_cards=local_page.diagnostics.cards_found,
            nationwide_cards=nationwide_page.diagnostics.cards_found,
            radius_effective=(
                local_page.diagnostics.cards_found != nationwide_page.diagnostics.cards_found
            ),
            local_url=local_url,
            nationwide_url=nationwide_url,
        )
