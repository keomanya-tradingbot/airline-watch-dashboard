from datetime import UTC, datetime, timedelta

from airline_watch.report import render_dashboard


def test_dashboard_renders_empty_state_and_health():
    now = datetime.now(UTC)
    html = render_dashboard(
        [],
        [
            {
                "source_name": "FAA",
                "source_url": "https://faa.gov",
                "status": "healthy",
                "detail": None,
                "checked_at": now.isoformat(),
            }
        ],
        now - timedelta(days=30),
        now,
    )

    assert "Airline Industry Watch" in html
    assert "No material changes detected" in html
    assert "All configured sources are healthy" in html
