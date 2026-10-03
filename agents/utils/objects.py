from __future__ import annotations

from pydantic import BaseModel


class Trade(BaseModel):
    id: int
    taker_order_id: str
    market: str
    asset_id: str
    side: str
    size: str
    fee_rate_bps: str
    price: str
    status: str
    match_time: str
    last_update: str
    outcome: str
    maker_address: str
    owner: str
    transaction_hash: str
    bucket_index: str
    maker_orders: list[str]
    type: str


class SimpleMarket(BaseModel):
    id: int
    question: str
    # start: str
    end: str
    description: str
    active: bool
    # deployed: Optional[bool]
    funded: bool
    # orderMinSize: float
    # orderPriceMinTickSize: float
    rewardsMinSize: float
    rewardsMaxSpread: float
    # volume: Optional[float]
    spread: float
    outcomes: str
    outcome_prices: str
    clob_token_ids: str | None


class ClobReward(BaseModel):
    id: str  # returned as string in api but really an int?
    conditionId: str
    assetAddress: str
    rewardsAmount: float  # only seen 0 but could be float?
    rewardsDailyRate: int  # only seen ints but could be float?
    startDate: str  # yyyy-mm-dd formatted date string
    endDate: str  # yyyy-mm-dd formatted date string


class Tag(BaseModel):
    id: str
    label: str | None = None
    slug: str | None = None
    forceShow: bool | None = None  # missing from current events data
    createdAt: str | None = None  # missing from events data
    updatedAt: str | None = None  # missing from current events data
    _sync: bool | None = None


class PolymarketEvent(BaseModel):
    id: str  # "11421"
    ticker: str | None = None
    slug: str | None = None
    title: str | None = None
    startDate: str | None = None
    creationDate: str | None = (
        None  # fine in market event but missing from events response
    )
    endDate: str | None = None
    image: str | None = None
    icon: str | None = None
    active: bool | None = None
    closed: bool | None = None
    archived: bool | None = None
    new: bool | None = None
    featured: bool | None = None
    restricted: bool | None = None
    liquidity: float | None = None
    volume: float | None = None
    reviewStatus: str | None = None
    createdAt: str | None = None  # 2024-07-08T01:06:23.982796Z,
    updatedAt: str | None = None  # 2024-07-15T17:12:48.601056Z,
    competitive: float | None = None
    volume24hr: float | None = None
    enableOrderBook: bool | None = None
    liquidityClob: float | None = None
    _sync: bool | None = None
    commentCount: int | None = None
    # markets: list[str, 'Market']  # forward reference; Market defined below
    markets: list[Market] | None = None
    tags: list[Tag] | None = None
    cyom: bool | None = None
    showAllOutcomes: bool | None = None
    showMarketImages: bool | None = None


class Market(BaseModel):
    id: int
    question: str | None = None
    conditionId: str | None = None
    slug: str | None = None
    resolutionSource: str | None = None
    endDate: str | None = None
    liquidity: float | None = None
    startDate: str | None = None
    image: str | None = None
    icon: str | None = None
    description: str | None = None
    outcomes: list | None = None
    outcomePrices: list | None = None
    volume: float | None = None
    active: bool | None = None
    closed: bool | None = None
    marketMakerAddress: str | None = None
    createdAt: str | None = None  # date type worth enforcing for dates?
    updatedAt: str | None = None
    new: bool | None = None
    featured: bool | None = None
    submitted_by: str | None = None
    archived: bool | None = None
    resolvedBy: str | None = None
    restricted: bool | None = None
    groupItemTitle: str | None = None
    groupItemThreshold: int | None = None
    questionID: str | None = None
    enableOrderBook: bool | None = None
    orderPriceMinTickSize: float | None = None
    orderMinSize: int | None = None
    volumeNum: float | None = None
    liquidityNum: float | None = None
    endDateIso: str | None = None  # iso format date = None
    startDateIso: str | None = None
    hasReviewedDates: bool | None = None
    volume24hr: float | None = None
    clobTokenIds: list | None = None
    umaBond: int | None = None  # returned as string from api?
    umaReward: int | None = None  # returned as string from api?
    volume24hrClob: float | None = None
    volumeClob: float | None = None
    liquidityClob: float | None = None
    acceptingOrders: bool | None = None
    negRisk: bool | None = None
    commentCount: int | None = None
    _sync: bool | None = None
    events: list[PolymarketEvent] | None = None
    ready: bool | None = None
    deployed: bool | None = None
    funded: bool | None = None
    deployedTimestamp: str | None = None  # utc z datetime string
    acceptingOrdersTimestamp: str | None = None  # utc z datetime string,
    cyom: bool | None = None
    competitive: float | None = None
    pagerDutyNotificationEnabled: bool | None = None
    reviewStatus: str | None = None  # deployed, draft, etc.
    approved: bool | None = None
    clobRewards: list[ClobReward] | None = None
    rewardsMinSize: int | None = (
        None  # would make sense to allow float but we'll see
    )
    rewardsMaxSpread: float | None = None
    spread: float | None = None


class ComplexMarket(BaseModel):
    id: int
    condition_id: str
    question_id: str
    tokens: str | list
    rewards: str
    minimum_order_size: str
    minimum_tick_size: str
    description: str
    category: str
    end_date_iso: str
    game_start_time: str
    question: str
    market_slug: str
    min_incentive_size: str
    max_incentive_spread: str
    active: bool
    closed: bool
    seconds_delay: int
    icon: str
    fpmm: str
    name: str
    description: str | None = None
    price: float
    tax: float | None = None


class SimpleEvent(BaseModel):
    id: int
    ticker: str
    slug: str
    title: str
    description: str
    end: str
    active: bool
    closed: bool
    archived: bool
    restricted: bool
    new: bool
    featured: bool
    markets: str


class Source(BaseModel):
    id: str | None
    name: str | None


class Article(BaseModel):
    source: Source | None
    author: str | None
    title: str | None
    description: str | None
    url: str | None
    urlToImage: str | None
    publishedAt: str | None
    content: str | None
