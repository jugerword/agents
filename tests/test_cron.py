"""Tests for cron scheduling logic (class name collision fix)."""

import sys
from unittest import mock

# The module imports Trader at top level; patch it before import.
with mock.patch.dict(sys.modules):
    trader_mod = mock.MagicMock()
    fake_trader = mock.MagicMock()
    fake_trader.one_best_trade = mock.Mock(return_value="trade done")
    trader_mod.Trader = mock.MagicMock(return_value=fake_trader)
    sys.modules["agents.application.trade"] = trader_mod

    from scheduler import Scheduler as SchedulerLib

    from agents.application.cron import TraderScheduler, TradingAgent


def test_scheduler_uses_library_class():
    s = TraderScheduler()
    # The inner scheduler must be the library's Scheduler, not our wrapper.
    assert isinstance(s.schedule, SchedulerLib)


def test_trading_agent_registers_weekly_job():
    ta = TradingAgent()
    jobs = list(ta.schedule.get_jobs())
    assert len(jobs) == 1
    # The registered handle should be the trader's one_best_trade
    assert jobs[0].handle is ta.trader.one_best_trade


def test_no_recursion_in_scheduler_init():
    # Previously `self.schedule = Scheduler()` recursed into the wrapper class.
    # Verify at runtime: constructing the wrapper must not blow the stack.
    s = TraderScheduler()
    assert s.schedule is not None
