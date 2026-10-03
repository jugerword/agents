"""Tests for the autonomous trader main path (one_best_trade).

All external calls (network, LLM, RAG) are mocked/stubbed so the test is
offline and deterministic. Verifies the full pipeline wiring (including order
execution with position caps), the bounded retry behavior, and failure paths.
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


def _happy_path(trader, balance=500.0, amount=12.5):
    fake_events = [{"id": 1}, {"id": 2}]
    fake_filtered_events = [{"id": 1}]
    fake_markets = [{"id": "m1"}]
    fake_filtered_markets = [{"metadata": {"question": "Q"}, "page_content": "d"}]
    trader.polymarket.get_all_tradeable_events.return_value = fake_events
    trader.polymarket.get_usdc_balance.return_value = balance
    trader.agent.filter_events_with_rag.return_value = fake_filtered_events
    trader.agent.map_filtered_events_to_markets.return_value = fake_markets
    trader.agent.filter_markets.return_value = fake_filtered_markets
    trader.agent.source_best_trade.return_value = "yes, 0.25"
    trader.agent.format_trade_prompt_for_execution.return_value = amount
    trader.polymarket.execute_market_order.return_value = "0xdeadbeef"
    return fake_filtered_markets


def test_one_best_trade_full_pipeline_with_order():
    trader = _make_trader()
    fake_filtered_markets = _happy_path(trader, balance=500.0, amount=12.5)

    trader.one_best_trade()

    trader.polymarket.get_all_tradeable_events.assert_called_once()
    trader.agent.filter_events_with_rag.assert_called_once()
    trader.agent.map_filtered_events_to_markets.assert_called_once()
    trader.agent.filter_markets.assert_called_once()
    trader.agent.source_best_trade.assert_called_once_with(fake_filtered_markets[0])
    # Order execution is active; the amount must be capped at the $5 ceiling.
    trader.polymarket.execute_market_order.assert_called_once()
    _, kwargs = trader.polymarket.execute_market_order.call_args
    (called_market, called_amount) = (
        trader.polymarket.execute_market_order.call_args[0]
    )
    assert called_market == fake_filtered_markets[0]
    assert called_amount <= 5.0


def test_position_cap_limits_to_ceiling():
    trader = _make_trader()
    trader.polymarket.get_usdc_balance.return_value = 500.0
    assert trader._cap_position(12.5) == 5.0  # ceiling caps it
    assert trader._cap_position(3.0) == 3.0  # below ceiling passes through


def test_position_cap_limits_to_10_percent_of_balance():
    trader = _make_trader()
    trader.polymarket.get_usdc_balance.return_value = 30.0
    # 10% of 30 = 3.0, below the $5 ceiling
    assert trader._cap_position(4.0) == pytest.approx(3.0)


def test_position_cap_aborts_on_zero_balance():
    trader = _make_trader()
    trader.polymarket.get_usdc_balance.return_value = 0.0  # query failed / empty
    assert trader._cap_position(10.0) == 0.0


def test_one_best_trade_skips_order_when_amount_zero():
    trader = _make_trader()
    _happy_path(trader, balance=0.0, amount=12.5)

    trader.one_best_trade()

    trader.polymarket.execute_market_order.assert_not_called()


def test_one_best_trade_retries_on_transient_failure():
    trader = _make_trader()
    fake_markets = [{"id": "m1"}]
    fake_filtered_markets = [{"metadata": {"question": "Q"}, "page_content": "d"}]
    trader.polymarket.get_all_tradeable_events.side_effect = [
        RuntimeError("proxy down"),
        [{"id": 1}],  # second attempt succeeds
    ]
    trader.polymarket.get_usdc_balance.return_value = 100.0
    trader.agent.filter_events_with_rag.return_value = [{"id": 1}]
    trader.agent.map_filtered_events_to_markets.return_value = fake_markets
    trader.agent.filter_markets.return_value = fake_filtered_markets
    trader.agent.source_best_trade.return_value = "no, 0.1"
    trader.agent.format_trade_prompt_for_execution.return_value = 1.0
    trader.polymarket.execute_market_order.return_value = "0xabc"

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
