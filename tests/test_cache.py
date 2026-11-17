
import sys
from pathlib import Path

import pytest

# Make the app directory importable.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import client


@pytest.fixture(autouse=True)
def reset_client():
    """Reset cache and statistics before every test."""
    client.cache.clear()
    client.old_answers.clear()

    for key in client.stats:
        client.stats[key] = 0

    client.config["baseline_mode"] = True
    client.config["baseline_server"] = {
        "ip": "127.0.0.1",
        "port": 5301
    }


def successful_reply(name, ip="10.0.1.11", ttl=30):
    return {
        "id": 1,
        "name": name,
        "ip": ip,
        "ttl": ttl,
        "status": "OK"
    }


def test_cache_miss(monkeypatch):
    """First request should contact the DNS server."""

    calls = []

    def fake_send_query(name, server_addr):
        calls.append(name)
        return successful_reply(name)

    monkeypatch.setattr(client, "send_query", fake_send_query)

    result = client.resolve("video.lab")

    assert result["status"] == "OK"
    assert result["from_cache"] is False
    assert result["ip"] == "10.0.1.11"

    assert len(calls) == 1
    assert client.stats["network_lookups"] == 1
    assert client.stats["cache_hits"] == 0

    print("PASS: Cache miss sends a network query")


def test_cache_hit(monkeypatch):
    """Repeated request should be served from cache."""

    calls = []

    def fake_send_query(name, server_addr):
        calls.append(name)
        return successful_reply(name)

    monkeypatch.setattr(client, "send_query", fake_send_query)

    first = client.resolve("video.lab")
    second = client.resolve("video.lab")

    assert first["from_cache"] is False
    assert second["from_cache"] is True

    assert second["status"] == "OK"
    assert second["ip"] == "10.0.1.11"

    assert len(calls) == 1
    assert client.stats["network_lookups"] == 1
    assert client.stats["cache_hits"] == 1

    print("PASS: Cache hit avoids a second network query")


def test_ttl_expiration(monkeypatch):
    """Expired cache entry should trigger a fresh network query."""

    calls = []

    def fake_send_query(name, server_addr):
        calls.append(name)
        return successful_reply(name, ip="10.0.1.22")

    monkeypatch.setattr(client, "send_query", fake_send_query)

    # Insert an entry with zero seconds of validity.
    client.save_to_cache("video.lab", "10.0.1.11", ttl=0)

    result = client.resolve("video.lab")

    assert result["status"] == "OK"
    assert result["from_cache"] is False
    assert result["ip"] == "10.0.1.22"

    assert len(calls) == 1
    assert client.stats["network_lookups"] == 1

    print("PASS: Expired cache entry triggers a fresh query")


def test_stale_answer_fallback(monkeypatch):
    """Previous answer should be returned if every network attempt times out."""

    client.old_answers["video.lab"] = "10.0.1.11"

    monkeypatch.setattr(
        client,
        "send_query",
        lambda name, server_addr: None
    )

    result = client.resolve("video.lab")

    assert result["status"] == "STALE"
    assert result["ip"] == "10.0.1.11"
    assert result["from_cache"] is True

    assert client.stats["failures"] == 1

    print("PASS: Stale answer is returned after network failure")


def test_not_found_is_not_cached(monkeypatch):
    """A NOT_FOUND response should not create a positive cache entry."""

    def fake_send_query(name, server_addr):
        return {
            "id": 1,
            "name": name,
            "ip": None,
            "ttl": 30,
            "status": "NOT_FOUND"
        }

    monkeypatch.setattr(client, "send_query", fake_send_query)

    result = client.resolve("unknown.lab")

    assert result["status"] == "NOT_FOUND"
    assert "unknown.lab" not in client.cache

    print("PASS: NOT_FOUND response is not cached")
