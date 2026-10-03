import httpx
import json
import time

from agents.polymarket.polymarket import Polymarket
from agents.utils.objects import Market, PolymarketEvent, ClobReward, Tag

# macOS env-proxy interacts badly with mihomo (SSL EOF / handshake timeouts);
# use an explicit HTTP proxy with env discovery disabled for every call.
_GAMMA_PROXIES = {"http://": "http://127.0.0.1:7890", "https://": "http://127.0.0.1:7890"}
_GAMMA_HTTPX = httpx.Client(
    proxy=_GAMMA_PROXIES,
    trust_env=False,
    timeout=45,
    limits=httpx.Limits(max_keepalive_connections=0),
)


class GammaMarketClient:
    def __init__(self):
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.gamma_markets_endpoint = self.gamma_url + "/markets"
        self.gamma_events_endpoint = self.gamma_url + "/events"

    def parse_pydantic_market(self, market_object: dict) -> Market:
        try:
            if "clobRewards" in market_object:
                clob_rewards: list[ClobReward] = []
                for clob_rewards_obj in market_object["clobRewards"]:
                    clob_rewards.append(ClobReward(**clob_rewards_obj))
                market_object["clobRewards"] = clob_rewards

            if "events" in market_object:
                events: list[PolymarketEvent] = []
                for market_event_obj in market_object["events"]:
                    events.append(self.parse_nested_event(market_event_obj))
                market_object["events"] = events

            # These two fields below are returned as stringified lists from the api
            if "outcomePrices" in market_object:
                market_object["outcomePrices"] = json.loads(
                    market_object["outcomePrices"]
                )
            if "clobTokenIds" in market_object:
                market_object["clobTokenIds"] = json.loads(
                    market_object["clobTokenIds"]
                )

            return Market(**market_object)
        except Exception as err:
            print(f"[parse_market] Caught exception: {err}")
            print("exception while handling object:", market_object)

    # Event parser for events nested under a markets api response
    def parse_nested_event(self, event_object: dict()) -> PolymarketEvent:
        print("[parse_nested_event] called with:", event_object)
        try:
            if "tags" in event_object:
                print("tags here", event_object["tags"])
                tags: list[Tag] = []
                for tag in event_object["tags"]:
                    tags.append(Tag(**tag))
                event_object["tags"] = tags

            return PolymarketEvent(**event_object)
        except Exception as err:
            print(f"[parse_event] Caught exception: {err}")
            print("\n", event_object)

    def parse_pydantic_event(self, event_object: dict) -> PolymarketEvent:
        try:
            if "tags" in event_object:
                print("tags here", event_object["tags"])
                tags: list[Tag] = []
                for tag in event_object["tags"]:
                    tags.append(Tag(**tag))
                event_object["tags"] = tags
            return PolymarketEvent(**event_object)
        except Exception as err:
            print(f"[parse_event] Caught exception: {err}")

    def get_markets(
        self, querystring_params={}, parse_pydantic=False, local_file_path=None
    ) -> "list[Market]":
        if parse_pydantic and local_file_path is not None:
            raise Exception(
                'Cannot use "parse_pydantic" and "local_file" params simultaneously.'
            )

        response = httpx.get(self.gamma_markets_endpoint, params=querystring_params)
        if response.status_code == 200:
            data = response.json()
            if local_file_path is not None:
                with open(local_file_path, "w+") as out_file:
                    json.dump(data, out_file)
            elif not parse_pydantic:
                return data
            else:
                markets: list[Market] = []
                for market_object in data:
                    markets.append(self.parse_pydantic_market(market_object))
                return markets
        else:
            print(f"Error response returned from api: HTTP {response.status_code}")
            raise Exception()

    def get_events(
        self, querystring_params={}, parse_pydantic=False, local_file_path=None
    ) -> "list[PolymarketEvent]":
        if parse_pydantic and local_file_path is not None:
            raise Exception(
                'Cannot use "parse_pydantic" and "local_file" params simultaneously.'
            )

        response = httpx.get(self.gamma_events_endpoint, params=querystring_params)
        if response.status_code == 200:
            data = response.json()
            if local_file_path is not None:
                with open(local_file_path, "w+") as out_file:
                    json.dump(data, out_file)
            elif not parse_pydantic:
                return data
            else:
                events: list[PolymarketEvent] = []
                for market_event_obj in data:
                    events.append(self.parse_event(market_event_obj))
                return events
        else:
            raise Exception()

    def get_all_markets(self, limit=2) -> "list[Market]":
        return self.get_markets(querystring_params={"limit": limit})

    def get_all_events(self, limit=2) -> "list[PolymarketEvent]":
        return self.get_events(querystring_params={"limit": limit})

    def get_current_markets(self, limit=4) -> "list[Market]":
        return self.get_markets(
            querystring_params={
                "active": True,
                "closed": False,
                "archived": False,
                "limit": limit,
            }
        )

    def get_all_current_markets(self, limit=100) -> "list[Market]":
        # Gamma API rejects offset pagination beyond 2000 ("offset too large,
        # use /markets/keyset for deeper pagination"), so paginate via keyset.
        # GET /markets/keyset?limit=N&after_cursor=<cursor> — the request
        # parameter is after_cursor (NOT keyset/next_cursor; those silently
        # return the same first page, causing an infinite loop). The response
        # carries the next cursor in the next_cursor field.
        # Retry transient proxy/SSL failures (observed: mihomo proxy drops
        # long-lived connections intermittently). A fresh client per call
        # avoids reusing a stale keep-alive connection that hangs forever.
        import time as _time

        cursor = ""
        all_markets = []
        while True:
            params = {
                "active": True,
                "closed": False,
                "archived": False,
                "limit": limit,
                "after_cursor": cursor,
            }
            market_batch = []
            for attempt in range(8):
                try:
                    # trust_env=False + explicit proxy: on macOS the env proxy
                    # mechanism (http_proxy/https_proxy) interacts badly with
                    # mihomo and causes SSL EOF / silent hangs; explicit proxy
                    # with env disabled is stable (verified with curl/httpx).
                    proxies = {
                        "http://": "http://127.0.0.1:7890",
                        "https://": "http://127.0.0.1:7890",
                    }
                    with httpx.Client(
                        proxy=proxies,
                        trust_env=False,
                        timeout=30,
                        limits=httpx.Limits(max_keepalive_connections=0),
                    ) as client:
                        response = client.get(
                            f"{self.gamma_url}/markets/keyset", params=params
                        )
                    if response.status_code != 200:
                        print(
                            "Error response returned from api: "
                            f"HTTP {response.status_code}"
                        )
                        raise Exception()
                    data = response.json()
                    market_batch = data.get("markets", [])
                    cursor = data.get("next_cursor", "")
                    break
                except Exception as err:
                    if attempt == 7:
                        raise
                    backoff = 2 ** (attempt + 1)  # 2s, 4s, 8s, 16s, 32s...
                    print(f"[keyset] batch retry {attempt+1} (backoff {backoff}s): {err}")
                    _time.sleep(backoff)

            all_markets.extend(market_batch)

            if not cursor or len(market_batch) < limit:
                break

        return all_markets

    def get_current_events(self, limit=4) -> "list[PolymarketEvent]":
        return self.get_events(
            querystring_params={
                "active": True,
                "closed": False,
                "archived": False,
                "limit": limit,
            }
        )

    def get_clob_tradable_markets(self, limit=2) -> "list[Market]":
        return self.get_markets(
            querystring_params={
                "active": True,
                "closed": False,
                "archived": False,
                "limit": limit,
                "enableOrderBook": True,
            }
        )

    def get_market(self, market_id: int) -> dict():
        url = self.gamma_markets_endpoint + "/" + str(market_id)
        # Retry a few times: the mihomo proxy intermittently drops TLS
        # handshakes; a single failure should not abort the whole trading run.
        last_err = None
        for attempt in range(4):
            try:
                response = _GAMMA_HTTPX.get(url)
                if response.status_code == 200:
                    return response.json()
                last_err = f"HTTP {response.status_code}"
            except Exception as err:
                last_err = str(err)[:120]
            if attempt < 3:
                time.sleep(1.5)
        raise RuntimeError(f"get_market({market_id}) failed after 4 attempts: {last_err}")


if __name__ == "__main__":
    gamma = GammaMarketClient()
    market = gamma.get_market("253123")
    poly = Polymarket()
    object = poly.map_api_to_market(market)
