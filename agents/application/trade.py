import contextlib
import os
import shutil

from agents.application.executor import Executor as Agent
from agents.polymarket.gamma import GammaMarketClient as Gamma
from agents.polymarket.polymarket import Polymarket


class Trader:
    def __init__(self):
        self.polymarket = Polymarket()
        self.gamma = Gamma()
        self.agent = Agent()

    def pre_trade_logic(self) -> None:
        self.clear_local_dbs()

    def clear_local_dbs(self) -> None:
        with contextlib.suppress(Exception):
            shutil.rmtree("local_db_events")
        with contextlib.suppress(Exception):
            shutil.rmtree("local_db_markets")

    def _cap_position(self, amount: float) -> float:
        """Hard caps on a single order.

        - MAX_TRADE_USD: absolute per-order ceiling (env, default $5).
        - 10% of USDC balance: never risk more than a tenth of the wallet.
        A balance query failure returns 0.0, which yields 0 and aborts the
        order — a safety default, never a lucky guess.
        """
        ceiling = float(os.getenv("MAX_TRADE_USD", "5"))
        capped = min(amount, ceiling)
        balance = self.polymarket.get_usdc_balance()
        if balance <= 0:
            print("[_cap_position] USDC balance query failed/zero; aborting order")
            return 0.0
        capped = min(capped, balance * 0.10)
        print(f"[_cap_position] amount={amount:.4f} -> capped={capped:.4f} "
              f"(ceiling={ceiling}, 10% of balance={balance * 0.10:.4f})")
        return capped

    def one_best_trade(self, max_attempts: int = 3) -> None:
        """
        one_best_trade is a strategy that evaluates all events, markets, and orderbooks

        leverages all available information sources accessible to the autonomous agent

        then executes that trade without any human intervention

        Retries are bounded (default 3) — the previous implementation recursed
        unboundedly, which spun forever when the network/proxy was down.
        """
        for attempt in range(1, max_attempts + 1):
            try:
                self.pre_trade_logic()

                events = self.polymarket.get_all_tradeable_events()
                print(f"1. FOUND {len(events)} EVENTS")

                filtered_events = self.agent.filter_events_with_rag(events)
                print(f"2. FILTERED {len(filtered_events)} EVENTS")

                markets = self.agent.map_filtered_events_to_markets(filtered_events)
                print()
                print(f"3. FOUND {len(markets)} MARKETS")

                print()
                filtered_markets = self.agent.filter_markets(markets)
                print(f"4. FILTERED {len(filtered_markets)} MARKETS")

                if not filtered_markets:
                    raise RuntimeError("no tradeable markets after filtering")

                market = filtered_markets[0]
                best_trade = self.agent.source_best_trade(market)
                print(f"5. CALCULATED TRADE {best_trade}")

                amount = self.agent.format_trade_prompt_for_execution(best_trade)
                amount = self._cap_position(amount)
                if amount <= 0:
                    print("6. ORDER SKIPPED (amount <= 0)")
                    return

                trade = self.polymarket.execute_market_order(market, amount)
                print(f"6. TRADED {trade}")
                return

            except Exception as e:
                print(f"Error {e} \n \n Retrying ({attempt}/{max_attempts})")
                if attempt == max_attempts:
                    raise RuntimeError(
                        f"one_best_trade failed after {max_attempts} attempts: {e}"
                    ) from e

    def maintain_positions(self):
        pass

    def incentive_farm(self):
        pass


if __name__ == "__main__":
    t = Trader()
    t.one_best_trade()
