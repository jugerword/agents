"""Tests for the news connector's endpoint selection and keyword search."""

from unittest import mock

from agents.connectors.news import News


def _mock_api():
    """Return a News instance whose underlying NewsApiClient is mocked."""
    api = mock.MagicMock()
    news = News.__new__(News)
    news.configs = {
        "language": "en",
        "country": "us",
        "top_headlines": "https://newsapi.org/v2/top-headlines?country=us&apiKey=",
        "base_url": "https://newsapi.org/v2/",
    }
    news.categories = {
        "business", "entertainment", "general", "health",
        "science", "sports", "technology",
    }
    news.API = api
    return news, api


def test_keyword_search_uses_everything_endpoint():
    """Without dates, keyword search must hit the 'everything' endpoint."""
    news, api = _mock_api()
    api.get_everything.return_value = {"articles": [{"title": "a"}]}
    # top-headlines must NOT be called for keyword search
    api.get_top_headlines.return_value = {"articles": []}

    result = news.get_articles_for_options(["bitcoin", "ethereum"])

    assert api.get_everything.call_count == 2
    api.get_top_headlines.assert_not_called()
    # Each keyword is passed as its own q
    qs = [c.kwargs["q"] for c in api.get_everything.call_args_list]
    assert qs == ["bitcoin", "ethereum"]
    assert result == {"bitcoin": [{"title": "a"}], "ethereum": [{"title": "a"}]}


def test_keyword_search_with_dates_uses_everything():
    """With dates, everything is used and from/to are forwarded."""
    news, api = _mock_api()
    api.get_everything.return_value = {"articles": [{"title": "x"}]}
    from datetime import datetime

    result = news.get_articles_for_options(
        ["btc"], date_start=datetime(2026, 1, 1), date_end=datetime(2026, 1, 31)
    )
    assert api.get_everything.call_count == 1
    kw = api.get_everything.call_args.kwargs
    assert kw["q"] == "btc"
    assert kw["from_param"] == datetime(2026, 1, 1)
    assert kw["to"] == datetime(2026, 1, 31)
    assert result == {"btc": [{"title": "x"}]}


def test_cli_keywords_split_and_parse():
    """Comma-separated keywords become separate searches returning Articles."""
    from agents.utils.objects import Article

    news, api = _mock_api()
    api.get_everything.return_value = {
        "articles": [
            {"title": "t", "description": "d", "url": "u",
             "urlToImage": None, "publishedAt": "2026-01-01T00:00:00Z",
             "content": "c", "author": "a",
             "source": {"id": "src1", "name": "s"}}
        ]
    }
    arts = news.get_articles_for_cli_keywords("btc,eth")
    assert len(arts) == 2
    assert all(isinstance(a, Article) for a in arts)
