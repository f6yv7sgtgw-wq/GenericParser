import httpx
import pytest

from generic_parser.sources.kleinanzeigen import (
    KleinanzeigenBlockedError,
    KleinanzeigenHttpClient,
)


def test_http_client_uses_delay_between_requests_not_per_card() -> None:
    calls: list[httpx.Request] = []
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, text="<html>ok</html>", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    http = KleinanzeigenHttpClient(
        client=client,
        request_delay_range=(3, 3),
        sleep=sleeps.append,
        random_choice=lambda values: values[0],
    )
    http.get("https://www.kleinanzeigen.de/s-a/k0")
    http.get("https://www.kleinanzeigen.de/s-b/k0")

    assert len(calls) == 2
    assert sleeps == [3]
    assert calls[0].headers["accept-language"].startswith("de-DE")


def test_http_client_retries_429_with_block_backoff() -> None:
    statuses = iter((429, 200))
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(next(statuses), text="<html>ok</html>", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    http = KleinanzeigenHttpClient(
        client=client,
        request_delay_range=(0, 0),
        blocked_backoff_seconds=30,
        max_attempts=2,
        sleep=sleeps.append,
    )
    result = http.get("https://www.kleinanzeigen.de/s-test/k0")

    assert result.status_code == 200
    assert sleeps == [30]


def test_http_client_raises_after_repeated_block() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Access denied", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    http = KleinanzeigenHttpClient(
        client=client,
        request_delay_range=(0, 0),
        blocked_backoff_seconds=0,
        max_attempts=2,
        sleep=lambda _: None,
    )
    with pytest.raises(KleinanzeigenBlockedError):
        http.get("https://www.kleinanzeigen.de/s-test/k0")
