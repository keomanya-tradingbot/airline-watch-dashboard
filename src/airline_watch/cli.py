from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .analyzer import analyze
from .collector import collect
from .config import load_sources
from .db import Store
from .report import render_dashboard, render_digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="airline-watch")
    parser.add_argument(
        "--config", type=Path, default=Path("config/sources.yaml")
    )
    parser.add_argument("--database", type=Path, default=Path("data/airline_watch.db"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Collect and analyze new observations")
    run.add_argument("--digest", action="store_true", help="Print a 24-hour digest")

    digest = subparsers.add_parser("digest", help="Render recent findings")
    digest.add_argument("--hours", type=int, default=24)
    digest.add_argument("--output", type=Path)

    dashboard = subparsers.add_parser("dashboard", help="Generate the HTML dashboard")
    dashboard.add_argument("--hours", type=int, default=24 * 30)
    dashboard.add_argument(
        "--output", type=Path, default=Path("outputs/dashboard.html")
    )
    return parser


def run_collection(args: argparse.Namespace, store: Store) -> int:
    sources = load_sources(args.config)
    created = 0
    failures = 0
    for source in sources:
        checked_at = datetime.now(UTC).isoformat()
        try:
            for observation in collect(source, store):
                observation_id = store.add_observation(observation)
                if observation_id is None:
                    continue
                store.save_analysis(observation_id, analyze(observation, source))
                created += 1
            store.save_source_run(
                source.name, source.url, "healthy", None, checked_at
            )
        except Exception as exc:
            failures += 1
            store.save_source_run(
                source.name, source.url, "failed", str(exc)[:500], checked_at
            )
            print(f"warning: {source.name}: {exc}", file=sys.stderr)
    print(f"Added {created} new observations; {failures} sources failed.")
    if args.digest:
        print_digest(store, 24, None)
    return 1 if failures == len(sources) and sources else 0


def print_digest(store: Store, hours: int, output: Path | None) -> None:
    since = datetime.now(UTC) - timedelta(hours=hours)
    report = render_digest(store.findings_since(since.isoformat()), since)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        print(f"Wrote {output}")
    else:
        print(report)


def write_dashboard(store: Store, hours: int, output: Path) -> None:
    since = datetime.now(UTC) - timedelta(hours=hours)
    report = render_dashboard(
        store.findings_since(since.isoformat()),
        store.source_runs(),
        since,
        datetime.now(UTC),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote {output}")


def main() -> None:
    args = build_parser().parse_args()
    store = Store(args.database)
    try:
        if args.command == "run":
            raise SystemExit(run_collection(args, store))
        if args.command == "digest":
            print_digest(store, args.hours, args.output)
        else:
            write_dashboard(store, args.hours, args.output)
    finally:
        store.close()


if __name__ == "__main__":
    main()
