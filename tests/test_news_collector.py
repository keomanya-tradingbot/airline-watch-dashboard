from datetime import UTC, datetime

from airline_watch.collector import collect_news_page
from airline_watch.models import Source


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


def test_news_page_collects_matching_articles(monkeypatch):
    listing = """
    <a href="/news/real-update">Airline announces a meaningful fleet update</a>
    <a href="/about">Learn more about the company</a>
    """
    article = """
    <html><head>
      <meta property="og:title" content="Airline orders new aircraft">
      <meta property="article:published_time" content="2026-06-12T10:00:00Z">
    </head><body><article>
      <p>The airline announced an order for twenty new aircraft for delivery.</p>
    </article></body></html>
    """

    def fake_fetch(url):
        return FakeResponse(article if url.endswith("real-update") else listing)

    monkeypatch.setattr("airline_watch.collector.fetch", fake_fetch)
    source = Source(
        name="Example newsroom",
        kind="news_page",
        tier="official",
        url="https://example.com/news",
        topics=["fleet_aircraft"],
        article_paths=["^/news/"],
    )

    results = collect_news_page(source, datetime.now(UTC))

    assert len(results) == 1
    assert results[0].title == "Airline orders new aircraft"
    assert results[0].published_at is not None
