from datetime import UTC, datetime
from pathlib import Path

from airline_watch.collector import collect_app_store
from airline_watch.db import Store
from airline_watch.models import Source


class FakeResponse:
    def __init__(self, version: str, notes: str):
        self.version = version
        self.notes = notes

    def json(self):
        return {
            "results": [
                {
                    "trackName": "Example Air",
                    "version": self.version,
                    "currentVersionReleaseDate": "2026-06-12T00:00:00Z",
                    "releaseNotes": self.notes,
                    "minimumOsVersion": "17.0",
                    "trackViewUrl": "https://apps.apple.com/app/id123?uo=4",
                }
            ]
        }


def test_app_store_establishes_baseline_then_reports_change(monkeypatch, tmp_path: Path):
    source = Source(
        name="Example app",
        kind="app_store",
        tier="official",
        url="https://itunes.apple.com/lookup?id=123",
        topics=["app"],
    )
    store = Store(tmp_path / "test.db")
    now = datetime.now(UTC)
    try:
        monkeypatch.setattr(
            "airline_watch.collector.fetch", lambda _: FakeResponse("1.0", "Initial")
        )
        assert collect_app_store(source, store, now) == []

        monkeypatch.setattr(
            "airline_watch.collector.fetch",
            lambda _: FakeResponse("1.1", "Improved check-in"),
        )
        observations = collect_app_store(source, store, now)
    finally:
        store.close()

    assert len(observations) == 1
    assert observations[0].title == "Example Air app updated to 1.1"
    assert "Improved check-in" in observations[0].body
