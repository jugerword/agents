from agents.application.trade import Trader

import time

from scheduler import Scheduler as SchedulerLib
from scheduler.trigger import Monday


class TraderScheduler:
    def __init__(self) -> None:
        self.trader = Trader()
        self.schedule = SchedulerLib()

    def start(self) -> None:
        while True:
            self.schedule.exec_jobs()
            time.sleep(1)


class TradingAgent(TraderScheduler):
    def __init__(self) -> None:
        super().__init__()
        self.weekly(Monday(), self.trader.one_best_trade)

    def weekly(self, trigger, handle, **kwargs):
        """Schedule a weekly job via the underlying scheduler library."""
        self.schedule.weekly(trigger, handle, **kwargs)
