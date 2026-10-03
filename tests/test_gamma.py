"""Tests for the GammaMarketClient network layer.

Verifies that get_markets/get_events go through the explicit-proxy client
(_get_with_retry) with bounded retries, and that the B006 mutable-default
bug (querystring_params={}) is gone.
"""

from unittest import mock

import pytest

from agents.polymarket.gamma import GammaMarketClient


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _FakeClient:
    """Minimal stand-in for httpx.Client with .get()."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, params=None):
        self.calls.append((url, params))
        # Consume one response per call; the last one repeats (success after N
        # failures is achieved by appending enough failure responses).
        resp = self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]
        if isinstance(resp, Exception):
            raise resp
        return resp


def _patch_client(responses):
    fake = _FakeClient(responses)
    patcher = mock.patch("agents.polymarket.gamma.httpx.Client", return_value=fake)
    return patcher, fake


def test_get_markets_uses_proxy_client_and_returns_data():
    gamma = GammaMarketClient()
    payload = [{"id": 1, "question": "Q"}]
    patcher, fake = _patch_client([_FakeResponse(payload=payload)])
    with patcher:
        out = gamma.get_markets(querystring_params={"limit": 5})
    assert out == payload
    # The request must go through our client (explicit proxy), not httpx.get.
    assert fake.calls, "get_markets must call httpx.Client, not bare httpx.get"
    url, params = fake.calls[0]
    assert "markets" in url
    assert params == {"limit": 5}


def test_get_events_uses_proxy_client_and_returns_data():
    gamma = GammaMarketClient()
    payload = [{"id": 10, "slug": "event"}]
    patcher, fake = _patch_client([_FakeResponse(payload=payload)])
    with patcher:
        out = gamma.get_events(querystring_params={"limit": 2})
    assert out == payload
    assert fake.calls


def test_get_markets_default_params_is_none_not_mutable():
    # Regression for B006: the default must be None, so two calls do not share
    # one mutable dict.
    import inspect

    sig = inspect.signature(GammaMarketClient.get_markets)
    assert sig.parameters["querystring_params"].default is None
    sig2 = inspect.signature(GammaMarketClient.get_events)
    assert sig2.parameters["querystring_params"].default is None


def test_retry_recovers_after_transient_failure():
    gamma = GammaMarketClient()
    payload = [{"id": 1}]
    responses = [
        RuntimeError("SSL EOF"),
        RuntimeError("timeout"),
        _FakeResponse(payload=payload),
    ]
    patcher, fake = _patch_client(responses)
    with patcher:
        out = gamma._get_with_retry("https://x/markets", {})
    assert out == payload
    assert len(fake.calls) == 3


def test_retry_gives_up_and_raises():
    gamma = GammaMarketClient()
    patcher, fake = _patch_client([RuntimeError("down")])
    with patcher, pytest.raises(RuntimeError):
        gamma._get_with_retry("https://x/markets", {}, attempts=2)
    assert len(fake.calls) == 2


def test_get_market_failure_raises_runtime_error():
    gamma = GammaMarketClient()
    # get_market uses the module-level _GAMMA_HTTPX client instance.
    with mock.patch(
        "agents.polymarket.gamma._GAMMA_HTTPX.get",
        side_effect=RuntimeError("down"),
    ), pytest.raises(RuntimeError):
        gamma.get_market("123")
