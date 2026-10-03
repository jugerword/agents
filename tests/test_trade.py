"""Tests for the autonomous trader main path (one_best_trade).

All external calls (network, LLM, RAG) are mocked/stubbed so the test is
offline and deterministic. Verifies the full pipeline wiring, the bounded
retry behavior, and the failure path.
"""

from unittest import mock

import pytest

from agents.application.trade import Trader


def _make_trader():
    trader = Trader.__new__(Trader)
    trader.polymarket = mock.MagicMock()
    trader.gamma = mock.MagicMock()
    trader.agent = mock.MagicMock()
    return trader


def test_one_best_trade_full_pipeline():
    trader = _make_trader()
    fake_events = [{"id": 1}, {"id": 2}]
    fake_filtered_events = [{"id": 1}]
    fake_markets = [{"id": "m1"}]
    fake_filtered_markets = [{"metadata": {"question": "Q"}, "page_content": "d"}]
    trader.polymarket.get_all_tradeable_events.return_value = fake_events
    trader.agent.filter_events_with_rag.return_value = fake_filtered_events
    trader.agent.map_filtered_events_to_markets.return_value = fake_markets
    trader.agent.filter_markets.return_value = fake_filtered_markets
    trader.agent.source_best_trade.return_value = "yes, 0.25"
    trader.agent.format_trade_prompt_for_execution.return_value = 12.5

    trader.one_best_trade()

    trader.polymarket.get_all_tradeable_events.assert_called_once()
    trader.agent.filter_events_with_rag.assert_called_once_with(fake_events)
    trader.agent.map_filtered_events_to_markets.assert_called_once_with(
        fake_filtered_events
    )
    trader.agent.filter_markets.assert_called_once_with(fake_markets)
    trader.agent.source_best_trade.assert_called_once_with(fake_filtered_markets[0])
    trader.agent.format_trade_prompt_for_execution.assert_called_once()
    # Trade execution is intentionally commented out (TOS); nothing else runs.
    trader.polymarket.execute_market_order.assert_not_called()


def test_one_best_trade_retries_on_transient_failure():
    trader = _make_trader()
    fake_markets = [{"id": "m1"}]
    fake_filtered_markets = [{"metadata": {"question": "Q"}, "page_content": "d"}]
    trader.polymarket.get_all_tradeable_events.side_effect = [
        RuntimeError("proxy down"),
        [{"id": 1}],  # second attempt succeeds
    ]
    trader.agent.filter_events_with_rag.return_value = [{"id": 1}]
    trader.agent.map_filtered_events_to_markets.return_value = fake_markets
    trader.agent.filter_markets.return_value = fake_filtered_markets
    trader.agent.source_best_trade.return_value = "no, 0.1"
    trader.agent.format_trade_prompt_for_execution.return_value = 1.0

    trader.one_best_trade(max_attempts=3)

    assert trader.polymarket.get_all_tradeable_events.call_count == 2


def test_one_best_trade_gives_up_after_max_attempts():
    trader = _make_trader()
    trader.polymarket.get_all_tradeable_events.side_effect = RuntimeError("down")

    with pytest.raises(RuntimeError):
        trader.one_best_trade(max_attempts=2)

    assert trader.polymarket.get_all_tradeable_events.call_count == 2


def test_one_best_trade_raises_when_no_markets():
    trader = _make_trader()
    trader.polymarket.get_all_tradeable_events.return_value = [{"id": 1}]
    trader.agent.filter_events_with_rag.return_value = [{"id": 1}]
    trader.agent.map_filtered_events_to_markets.return_value = []
    trader.agent.filter_markets.return_value = []

    with pytest.raises(RuntimeError):
        trader.one_best_trade()
