from __future__ import annotations

import difflib
import json
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

import feedparser
import requests
from bs4 import BeautifulSoup

from .db import Store
from .models import Observation, Source
from .text import canonical_url, fingerprint, visible_text


USER_AGENT = "AirlineWatch/0.1 (+industry change monitor)"


def fetch(url: str) -> requests.Response:
    response = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xml"},
    )
    response.raise_for_status()
    return response


def collect_feed(source: Source, now: datetime) -> list[Observation]:
    response = fetch(source.url)
    feed = feedparser.parse(response.content)
    observations = []
    for entry in feed.entries[: source.max_items]:
        url = canonical_url(entry.get("link", source.url))
        title = entry.get("title", "Untitled update").strip()
        if any(
            keyword.lower() in title.lower()
            for keyword in source.exclude_title_keywords
        ):
            continue
        body = visible_text(entry.get("summary", "") or entry.get("description", ""))
        published = _parse_date(entry.get("published") or entry.get("updated"))
        observations.append(
            Observation(
                source_name=source.name,
                source_tier=source.tier,
                title=title,
                url=url,
                published_at=published,
                collected_at=now,
                body=body,
                fingerprint=fingerprint(url, title, body),
            )
        )
    return observations


def collect_page(source: Source, store: Store, now: datetime) -> list[Observation]:
    response = fetch(source.url)
    body = visible_text(response.text)
    content_hash = fingerprint(body)
    previous = store.snapshot(source.url)
    store.save_snapshot(source.url, content_hash, body, now.isoformat())
    if previous is None or previous[0] == content_hash:
        return []

    diff_lines = list(
        difflib.unified_diff(
            previous[1].splitlines(),
            body.splitlines(),
            fromfile="previous",
            tofile="current",
            n=2,
            lineterm="",
        )
    )
    diff = "\n".join(diff_lines)
    if len(diff_lines) < 5:
        return []
    diff = diff[:20_000]
    return [
        Observation(
            source_name=source.name,
            source_tier=source.tier,
            title=f"Website change detected: {source.name}",
            url=canonical_url(source.url),
            collected_at=now,
            body=diff,
            fingerprint=fingerprint(source.url, content_hash),
        )
    ]


def collect_news_page(source: Source, now: datetime) -> list[Observation]:
    response = fetch(source.url)
    soup = BeautifulSoup(response.text, "html.parser")
    source_host = urlsplit(source.url).netloc.lower()
    candidates: dict[str, str] = {}

    for link in soup.find_all("a", href=True):
        title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
        if len(title) < 18 or len(title) > 240:
            continue
        url = canonical_url(urljoin(source.url, link["href"]))
        parts = urlsplit(url)
        if parts.netloc.lower() != source_host:
            continue
        path = parts.path.lower()
        if source.article_paths and not any(
            re.search(pattern, path) for pattern in source.article_paths
        ):
            continue
        if _looks_like_navigation(title):
            continue
        if any(
            keyword.lower() in title.lower()
            for keyword in source.exclude_title_keywords
        ):
            continue
        candidates.setdefault(url, title)
        if len(candidates) >= source.max_items:
            break

    observations = []
    for url, listing_title in candidates.items():
        try:
            article = fetch(url)
            article_soup = BeautifulSoup(article.text, "html.parser")
            title = _article_title(article_soup) or listing_title
            body = _article_body(article_soup)
            published = _article_date(article_soup)
        except requests.RequestException:
            title = listing_title
            body = listing_title
            published = None
        observations.append(
            Observation(
                source_name=source.name,
                source_tier=source.tier,
                title=title,
                url=url,
                published_at=published,
                collected_at=now,
                body=body[:20_000],
                fingerprint=fingerprint(url),
            )
        )
    return observations


def collect_app_store(
    source: Source, store: Store, now: datetime
) -> list[Observation]:
    response = fetch(source.url)
    payload = response.json()
    results = payload.get("results", [])
    if not results:
        raise RuntimeError("App Store lookup returned no results")
    app = results[0]
    current = {
        "name": app.get("trackName"),
        "version": app.get("version"),
        "released_at": app.get("currentVersionReleaseDate"),
        "release_notes": app.get("releaseNotes"),
        "minimum_os": app.get("minimumOsVersion"),
        "url": app.get("trackViewUrl"),
    }
    body = json.dumps(current, ensure_ascii=True, sort_keys=True, indent=2)
    content_hash = fingerprint(body)
    previous = store.snapshot(source.url)
    store.save_snapshot(source.url, content_hash, body, now.isoformat())
    if previous is None or previous[0] == content_hash:
        return []

    before = json.loads(previous[1])
    changed = [
        f"{key}: {before.get(key)!r} -> {current.get(key)!r}"
        for key in current
        if before.get(key) != current.get(key)
    ]
    version = current.get("version") or "new release"
    return [
        Observation(
            source_name=source.name,
            source_tier=source.tier,
            title=f"{current.get('name') or source.name} app updated to {version}",
            url=canonical_url(current.get("url") or source.url),
            published_at=_parse_iso_date(current.get("released_at")),
            collected_at=now,
            body="\n".join(changed),
            fingerprint=fingerprint(source.url, content_hash),
        )
    ]


def collect(source: Source, store: Store) -> list[Observation]:
    now = datetime.now(UTC)
    if source.kind == "feed":
        return collect_feed(source, now)
    if source.kind == "news_page":
        return collect_news_page(source, now)
    if source.kind == "app_store":
        return collect_app_store(source, store, now)
    return collect_page(source, store, now)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def _parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _looks_like_navigation(title: str) -> bool:
    lowered = title.lower()
    blocked = (
        "view all",
        "read more",
        "learn more",
        "contact us",
        "privacy",
        "subscribe",
        "media resources",
        "terms of",
    )
    return any(term in lowered for term in blocked)


def _article_title(soup: BeautifulSoup) -> str | None:
    for attrs in (
        {"property": "og:title"},
        {"name": "twitter:title"},
    ):
        node = soup.find("meta", attrs=attrs)
        if node and node.get("content"):
            return re.sub(r"\s+", " ", str(node["content"])).strip()
    heading = soup.find("h1")
    return heading.get_text(" ", strip=True) if heading else None


def _article_body(soup: BeautifulSoup) -> str:
    for node in soup(["script", "style", "nav", "footer", "header", "aside"]):
        node.decompose()
    main = soup.find("article") or soup.find("main") or soup.body
    if not main:
        return ""
    paragraphs = [
        re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
        for node in main.find_all(["p", "li"])
    ]
    meaningful = [text for text in paragraphs if len(text) >= 35]
    return "\n".join(meaningful) or visible_text(str(main))


def _article_date(soup: BeautifulSoup) -> datetime | None:
    for attrs in (
        {"property": "article:published_time"},
        {"name": "date"},
        {"name": "publish-date"},
    ):
        node = soup.find("meta", attrs=attrs)
        if node and node.get("content"):
            parsed = _parse_iso_date(str(node["content"]))
            if parsed:
                return parsed
    time_node = soup.find("time", datetime=True)
    return _parse_iso_date(str(time_node["datetime"])) if time_node else None
