#!/usr/bin/env python3
"""Verify a long production module-v2 continuation chain without printing data."""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from typing import Any

import httpx


def normalized_keys(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield "".join(character for character in str(key).casefold() if character.isalnum())
            yield from normalized_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from normalized_keys(item)


def request_body(query: str) -> dict[str, Any]:
    return {
        "contract": "generic-parser-module-v2",
        "batch_id": f"production-mobile-long-run-{int(time.time())}",
        "client": {
            "project_id": "genericparser-production-mobile-gate",
            "project_version": "1.6.3",
        },
        "search": {
            "search_id": "mobile-three-source-long-run",
            "query": query,
            "sources": ["kleinanzeigen", "vinted", "ebay"],
            "criteria": {
                "required_terms": [],
                "excluded_terms": [],
                "model_patterns": [],
                "brands": [],
            },
            "filters": {
                "max_price": None,
                "accept_bundles": False,
                "accept_incomplete": False,
                "include_auctions": False,
                "include_review": True,
                "include_rejected": True,
            },
            "location": {},
            "sort_by": "relevance",
        },
        "continuation_token": None,
        "debug": {"enabled": False},
    }


def validate_packet(data: dict[str, Any], expected_batch: str) -> tuple[str, list[dict[str, Any]]]:
    if data.get("contract") != "generic-parser-module-v2":
        raise RuntimeError("unexpected module contract")
    if data.get("batch_id") != expected_batch:
        raise RuntimeError("batch identity changed during continuation")
    if data.get("status") not in {"partial", "complete"}:
        raise RuntimeError("unexpected packet status")
    packets = data.get("results") or []
    if len(packets) != 1 or not isinstance(packets[0], dict):
        raise RuntimeError("packet must contain exactly one source result")
    packet = packets[0]
    source = str(packet.get("source") or "")
    if source not in {"kleinanzeigen", "vinted", "ebay"}:
        raise RuntimeError("unknown source in packet")
    listings = packet.get("listings") or []
    if not isinstance(listings, list):
        raise RuntimeError("packet listings are not an array")
    for listing in listings:
        key = str(listing.get("listing_key") or "")
        if not key.startswith(f"{source}:"):
            raise RuntimeError("listing_key does not match packet source")
        forbidden = {"seller", "sellerusername", "sellerid", "username", "userid", "eiastoken", "feedbackscore"}
        if set(normalized_keys(listing)) & forbidden:
            raise RuntimeError("forbidden seller data in v2 listing")
    return source, listings


def run(url: str, query: str, max_packets: int, min_packets: int) -> dict[str, Any]:
    endpoint = f"{url.rstrip('/')}/api/module/v2/search"
    body = request_body(query)
    sources: Counter[str] = Counter()
    unique: set[str] = set()
    packets = 0
    complete = False
    transport_retries = 0
    with httpx.Client(timeout=httpx.Timeout(90.0, connect=20.0), follow_redirects=False) as client:
        while packets < max_packets:
            response = None
            last_error: Exception | None = None
            for delay in (0.0, 0.25, 0.75, 1.5):
                if delay:
                    transport_retries += 1
                    time.sleep(delay)
                try:
                    response = client.post(endpoint, json=body)
                    break
                except httpx.TransportError as error:
                    last_error = error
            if response is None:
                raise RuntimeError(f"transport retries exhausted: {type(last_error).__name__}")
            if response.status_code != 200:
                raise RuntimeError(f"module-v2 packet returned HTTP {response.status_code}")
            data = response.json()
            source, listings = validate_packet(data, body["batch_id"])
            packets += 1
            sources[source] += len(listings)
            unique.update(str(item["listing_key"]) for item in listings)
            token = data.get("continuation_token")
            complete = data.get("status") == "complete"
            if complete:
                if token is not None:
                    raise RuntimeError("complete packet unexpectedly returned a continuation token")
                break
            if not isinstance(token, str) or not token.startswith("v2."):
                raise RuntimeError("partial packet did not return a signed continuation token")
            body["continuation_token"] = token
    if packets < min_packets and not complete:
        raise RuntimeError(f"long-run gate stopped after only {packets} packets")
    return {
        "status": "complete" if complete else "controlled_stop",
        "packets": packets,
        "minimum_packets": min_packets,
        "unique_listings": len(unique),
        "source_rows": dict(sources),
        "transport_retries": transport_retries,
        "query": query,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("deployment_url")
    parser.add_argument("--query", default="Evercade")
    parser.add_argument("--max-packets", type=int, default=36)
    parser.add_argument("--min-packets", type=int, default=30)
    args = parser.parse_args()
    try:
        summary = run(args.deployment_url, args.query, args.max_packets, args.min_packets)
    except Exception as error:
        print(f"module-v2 long-run failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
