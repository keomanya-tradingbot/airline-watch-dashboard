from datetime import UTC, datetime

from airline_watch.analyzer import heuristic_analysis
from airline_watch.models import Observation, Source


def test_heuristic_classifies_leadership_change():
    source = Source(
        name="Airline newsroom",
        kind="page",
        tier="official",
        url="https://example.com",
    )
    observation = Observation(
        source_name=source.name,
        source_tier=source.tier,
        title="Airline appoints new CEO",
        url=source.url,
        collected_at=datetime.now(UTC),
        body="The company appointed a new chief executive.",
        fingerprint="abc",
    )

    result = heuristic_analysis(observation, source)

    assert result.category == "leadership"
    assert result.confirmed is True
