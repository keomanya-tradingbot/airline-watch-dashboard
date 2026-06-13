from __future__ import annotations

import os
import re

from .models import Analysis, Category, Observation, Source


KEYWORDS: dict[Category, tuple[str, ...]] = {
    "policy": (
        "policy",
        "rule",
        "regulation",
        "fee",
        "refund",
        "contract of carriage",
    ),
    "fleet_aircraft": (
        "aircraft",
        "fleet",
        "boeing",
        "airbus",
        "engine",
        "delivery",
        "order",
    ),
    "leadership": ("ceo", "president", "chief", "executive", "appoint", "resign"),
    "app": ("mobile app", "ios", "android", "app store", "digital check-in"),
    "website": ("website", "web site", "booking flow", "online"),
    "operations": ("route", "schedule", "airport", "flight", "capacity", "service"),
    "safety_regulatory": (
        "safety",
        "incident",
        "accident",
        "airworthiness",
        "inspection",
        "faa",
        "ntsb",
    ),
    "financial_strategy": (
        "earnings",
        "revenue",
        "merger",
        "acquisition",
        "partnership",
        "strategy",
    ),
    "customer_experience": (
        "loyalty",
        "miles",
        "lounge",
        "seat",
        "boarding",
        "baggage",
        "customer",
    ),
    "other": (),
}


SYSTEM_PROMPT = """You analyze airline-industry updates.
Classify only material changes involving airlines, aircraft manufacturers,
airports, aviation regulators, or passenger-facing airline products.

Be factual and source-bound. Do not infer that a proposal is final. Set
confirmed=false for rumors, proposals, consultations, or unverified reporting.
For website diffs, summarize the actual added/removed meaning and ignore
navigation, timestamps, rotating promotions, cookie text, and layout noise.
Importance: 5 urgent safety/regulatory or major industry impact; 4 major policy,
fleet, leadership, or product change; 3 meaningful operational/customer change;
2 limited update; 1 noise. Use a concise summary and explain practical impact."""


def analyze(observation: Observation, source: Source) -> Analysis:
    if os.getenv("OPENAI_API_KEY"):
        return _model_analysis(observation, source)
    return heuristic_analysis(observation, source)


def _model_analysis(observation: Observation, source: Source) -> Analysis:
    from openai import OpenAI

    client = OpenAI()
    response = client.responses.parse(
        model=os.getenv("AIRLINE_WATCH_MODEL", "gpt-5.5"),
        reasoning={"effort": "low"},
        input=[
            {"role": "developer", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Source: {source.name}\n"
                    f"Source tier: {source.tier}\n"
                    f"Expected topics: {', '.join(source.topics)}\n"
                    f"Title: {observation.title}\n"
                    f"URL: {observation.url}\n\n"
                    f"Content:\n{observation.body[:25_000]}"
                ),
            },
        ],
        text_format=Analysis,
    )
    if response.output_parsed is None:
        raise RuntimeError("Model returned no structured analysis")
    return response.output_parsed


def heuristic_analysis(observation: Observation, source: Source) -> Analysis:
    haystack = f"{observation.title}\n{observation.body}".lower()
    scores = {
        category: sum(haystack.count(keyword) for keyword in keywords)
        for category, keywords in KEYWORDS.items()
        if category != "other"
    }
    category = max(scores, key=scores.get) if any(scores.values()) else "other"
    relevant = category != "other" or bool(source.topics)
    clean = re.sub(r"^[+\-@].*$", " ", observation.body, flags=re.MULTILINE)
    clean = re.sub(r"\s+", " ", clean).strip()
    summary = clean[:280] if clean else observation.title
    if len(clean) > 280:
        summary = summary.rsplit(" ", 1)[0] + "..."
    importance = 2
    if category in {"policy", "fleet_aircraft", "leadership"}:
        importance = 3
    if category == "safety_regulatory":
        importance = 4
    impacts = {
        "policy": "May change airline obligations, passenger rights, fees, or compliance requirements.",
        "fleet_aircraft": "Could affect fleet capability, aircraft availability, operating economics, or future capacity.",
        "leadership": "A leadership change can alter company priorities, execution, and strategic direction.",
        "app": "Changes the digital travel experience for booking, check-in, disruption handling, or loyalty members.",
        "website": "May change how customers find information, book travel, or manage existing trips.",
        "operations": "Could affect routes, schedules, airport operations, capacity, or day-of-travel reliability.",
        "safety_regulatory": "May affect aviation safety practices, regulatory oversight, or operational restrictions.",
        "financial_strategy": "Could influence airline competition, investment priorities, partnerships, or financial performance.",
        "customer_experience": "May change the passenger experience, loyalty benefits, seating, baggage, or airport journey.",
        "other": "Review the cited source to determine its practical airline-industry impact.",
    }
    return Analysis(
        relevant=relevant,
        category=category,
        entities=[],
        summary=summary,
        why_it_matters=impacts[category],
        importance=importance,
        confirmed=source.tier in {"regulator", "official", "industry"},
    )
