from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Analysis, Finding, Observation


SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT NOT NULL UNIQUE,
    source_name TEXT NOT NULL,
    source_tier TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TEXT,
    collected_at TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
    observation_id INTEGER PRIMARY KEY REFERENCES observations(id),
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    source_url TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    body TEXT NOT NULL,
    collected_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_runs (
    source_name TEXT PRIMARY KEY,
    source_url TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT,
    checked_at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def add_observation(self, observation: Observation) -> int | None:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO observations
            (fingerprint, source_name, source_tier, title, url, published_at,
             collected_at, body)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation.fingerprint,
                observation.source_name,
                observation.source_tier,
                observation.title,
                observation.url,
                observation.published_at.isoformat()
                if observation.published_at
                else None,
                observation.collected_at.isoformat(),
                observation.body,
            ),
        )
        self.connection.commit()
        return cursor.lastrowid if cursor.rowcount else None

    def save_analysis(self, observation_id: int, analysis: Analysis) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO analyses (observation_id, payload) VALUES (?, ?)",
            (observation_id, analysis.model_dump_json()),
        )
        self.connection.commit()

    def snapshot(self, url: str) -> tuple[str, str] | None:
        row = self.connection.execute(
            "SELECT content_hash, body FROM snapshots WHERE source_url = ?", (url,)
        ).fetchone()
        return (row[0], row[1]) if row else None

    def save_snapshot(
        self, url: str, content_hash: str, body: str, collected_at: str
    ) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO snapshots
            (source_url, content_hash, body, collected_at) VALUES (?, ?, ?, ?)
            """,
            (url, content_hash, body, collected_at),
        )
        self.connection.commit()

    def save_source_run(
        self,
        source_name: str,
        source_url: str,
        status: str,
        detail: str | None,
        checked_at: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO source_runs
            (source_name, source_url, status, detail, checked_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source_name, source_url, status, detail, checked_at),
        )
        self.connection.commit()

    def source_runs(self) -> list[dict[str, str | None]]:
        rows = self.connection.execute(
            """
            SELECT source_name, source_url, status, detail, checked_at
            FROM source_runs
            ORDER BY status DESC, source_name
            """
        ).fetchall()
        return [
            {
                "source_name": row[0],
                "source_url": row[1],
                "status": row[2],
                "detail": row[3],
                "checked_at": row[4],
            }
            for row in rows
        ]

    def findings_since(self, since_iso: str) -> list[Finding]:
        rows = self.connection.execute(
            """
            SELECT o.id, o.fingerprint, o.source_name, o.source_tier, o.title,
                   o.url, o.published_at, o.collected_at, o.body, a.payload
            FROM observations o
            JOIN analyses a ON a.observation_id = o.id
            WHERE o.collected_at >= ?
            ORDER BY json_extract(a.payload, '$.importance') DESC,
                     o.collected_at DESC
            """,
            (since_iso,),
        ).fetchall()
        findings = []
        for row in rows:
            observation = Observation.model_validate(
                {
                    "fingerprint": row[1],
                    "source_name": row[2],
                    "source_tier": row[3],
                    "title": row[4],
                    "url": row[5],
                    "published_at": row[6],
                    "collected_at": row[7],
                    "body": row[8],
                }
            )
            findings.append(
                Finding(
                    observation_id=row[0],
                    observation=observation,
                    analysis=Analysis.model_validate(json.loads(row[9])),
                )
            )
        return findings
