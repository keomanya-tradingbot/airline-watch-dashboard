from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from html import escape

from .models import Finding


def render_digest(findings: list[Finding], since: datetime) -> str:
    relevant = [finding for finding in findings if finding.analysis.relevant]
    lines = [
        "# Airline Industry Change Digest",
        "",
        f"Period beginning: {since.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Material findings: {len(relevant)}",
        "",
    ]
    if not relevant:
        lines.append("No material changes were detected.")
        return "\n".join(lines) + "\n"

    grouped: dict[str, list[Finding]] = defaultdict(list)
    for finding in relevant:
        grouped[finding.analysis.category].append(finding)

    for category, items in grouped.items():
        lines.extend(["## " + category.replace("_", " ").title(), ""])
        for finding in items:
            analysis = finding.analysis
            observation = finding.observation
            status = "confirmed" if analysis.confirmed else "developing"
            lines.extend(
                [
                    f"### [{observation.title}]({observation.url})",
                    "",
                    f"**Importance:** {analysis.importance}/5 | "
                    f"**Status:** {status} | "
                    f"**Source:** {observation.source_name} "
                    f"({observation.source_tier})",
                    "",
                    analysis.summary,
                    "",
                    f"**Why it matters:** {analysis.why_it_matters}",
                    "",
                ]
            )
            if analysis.effective_date:
                lines.extend(
                    [f"**Effective date:** {analysis.effective_date}", ""]
                )
    return "\n".join(lines)


def render_dashboard(
    findings: list[Finding],
    source_runs: list[dict[str, str | None]],
    since: datetime,
    generated_at: datetime,
) -> str:
    relevant = [
        finding
        for finding in findings
        if finding.analysis.relevant and finding.analysis.category != "other"
    ][:30]
    categories = sorted({item.analysis.category for item in relevant})
    healthy = sum(run["status"] == "healthy" for run in source_runs)
    failed = sum(run["status"] == "failed" for run in source_runs)
    high_priority = sum(item.analysis.importance >= 4 for item in relevant)

    cards = []
    for finding in relevant:
        observation = finding.observation
        analysis = finding.analysis
        category = analysis.category
        published = observation.published_at or observation.collected_at
        cards.append(
            f"""
            <article class="news-card" data-category="{escape(category)}">
              <div class="card-top">
                <span class="category">{escape(category.replace("_", " ").title())}</span>
                <span class="importance importance-{analysis.importance}">
                  Priority {analysis.importance}/5
                </span>
              </div>
              <h2><a href="{escape(observation.url)}" target="_blank" rel="noreferrer">
                {escape(observation.title)}
              </a></h2>
              <p class="summary">{escape(analysis.summary)}</p>
              <p class="impact"><strong>Why it matters:</strong>
                {escape(analysis.why_it_matters)}
              </p>
              <div class="meta">
                <span>{escape(observation.source_name)}</span>
                <span>{escape(observation.source_tier.title())}</span>
                <span>{published.astimezone(UTC).strftime("%b %d, %Y")}</span>
                <span>{"Confirmed" if analysis.confirmed else "Developing"}</span>
              </div>
            </article>
            """
        )

    if not cards:
        cards.append(
            """
            <section class="empty">
              <h2>No material changes detected</h2>
              <p>The monitor is active. New policy, fleet, leadership, app,
              website, safety, and customer-experience changes will appear here
              after the next daily check.</p>
            </section>
            """
        )

    filters = ['<button class="filter active" data-filter="all">All</button>']
    filters.extend(
        f'<button class="filter" data-filter="{escape(category)}">'
        f'{escape(category.replace("_", " ").title())}</button>'
        for category in categories
    )

    failed_rows = "".join(
        f"<li><strong>{escape(str(run['source_name']))}</strong>: "
        f"{escape(str(run['detail'] or 'Unavailable'))}</li>"
        for run in source_runs
        if run["status"] == "failed"
    )
    health_detail = (
        f"<details><summary>{failed} source warnings</summary><ul>{failed_rows}</ul></details>"
        if failed
        else "<span class='all-good'>All configured sources are healthy.</span>"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Airline Industry Watch</title>
  <style>
    :root {{
      --ink: #12233f; --muted: #627087; --line: #dfe5ec;
      --paper: #f5f7fa; --card: #fff; --navy: #0a2d55;
      --blue: #1769aa; --sky: #dcedfa; --red: #b42318;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--paper); color: var(--ink);
      font: 15px/1.55 Inter, ui-sans-serif, system-ui, sans-serif; }}
    header {{ background: linear-gradient(135deg, #071d36, #0d4778);
      color: white; padding: 52px 24px 44px; }}
    .wrap {{ width: min(1120px, calc(100% - 40px)); margin: auto; }}
    .eyebrow {{ color: #9fd4fb; font-weight: 700; letter-spacing: .12em;
      text-transform: uppercase; font-size: 12px; }}
    h1 {{ margin: 8px 0 6px; font-size: clamp(34px, 6vw, 58px);
      line-height: 1.05; letter-spacing: -.035em; }}
    .subtitle {{ color: #d9e8f5; max-width: 700px; font-size: 17px; }}
    .updated {{ color: #a8c6df; margin-top: 22px; font-size: 13px; }}
    .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;
      margin-top: -24px; }}
    .stat {{ background: var(--card); border: 1px solid var(--line);
      border-radius: 14px; padding: 20px; box-shadow: 0 8px 24px #16324f12; }}
    .stat strong {{ display: block; font-size: 28px; }}
    .stat span {{ color: var(--muted); }}
    main {{ padding: 34px 0 60px; }}
    .toolbar {{ display: flex; gap: 9px; flex-wrap: wrap; margin: 26px 0; }}
    .filter {{ border: 1px solid #cdd6e0; background: white; color: var(--ink);
      border-radius: 999px; padding: 9px 14px; cursor: pointer; font-weight: 650; }}
    .filter.active {{ background: var(--navy); color: white; border-color: var(--navy); }}
    .news-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }}
    .news-card, .empty {{ background: var(--card); border: 1px solid var(--line);
      border-radius: 16px; padding: 24px; box-shadow: 0 5px 18px #16324f0b; }}
    .card-top, .meta {{ display: flex; align-items: center; gap: 9px; flex-wrap: wrap; }}
    .category {{ background: var(--sky); color: #154e7a; border-radius: 6px;
      padding: 4px 8px; font-size: 12px; font-weight: 750; }}
    .importance {{ margin-left: auto; color: var(--muted); font-size: 12px; font-weight: 700; }}
    .importance-4, .importance-5 {{ color: var(--red); }}
    h2 {{ font-size: 21px; line-height: 1.25; margin: 16px 0 12px; }}
    h2 a {{ color: var(--ink); text-decoration: none; }}
    h2 a:hover {{ color: var(--blue); }}
    .summary {{ font-size: 16px; }}
    .impact {{ color: #42536b; }}
    .meta {{ border-top: 1px solid var(--line); margin-top: 18px;
      padding-top: 14px; color: var(--muted); font-size: 12px; }}
    .health {{ margin-top: 34px; border-top: 1px solid var(--line); padding-top: 24px; }}
    details ul {{ max-height: 180px; overflow: auto; color: var(--muted); }}
    .all-good {{ color: #16794b; font-weight: 650; }}
    footer {{ color: var(--muted); padding: 0 0 40px; }}
    @media (max-width: 760px) {{
      .stats {{ grid-template-columns: repeat(2, 1fr); }}
      .news-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <div class="eyebrow">Daily intelligence brief</div>
      <h1>Airline Industry Watch</h1>
      <div class="subtitle">Material changes across airline policy, fleets,
      leadership, digital products, operations, safety, and customer experience.</div>
      <div class="updated">Updated {generated_at.astimezone(UTC).strftime("%B %d, %Y at %H:%M UTC")}
      · Coverage since {since.astimezone(UTC).strftime("%B %d, %Y")}</div>
    </div>
  </header>
  <div class="wrap">
    <section class="stats">
      <div class="stat"><strong>{len(relevant)}</strong><span>Material updates</span></div>
      <div class="stat"><strong>{high_priority}</strong><span>High priority</span></div>
      <div class="stat"><strong>{healthy}</strong><span>Healthy sources</span></div>
      <div class="stat"><strong>{failed}</strong><span>Source warnings</span></div>
    </section>
    <main>
      <nav class="toolbar">{"".join(filters)}</nav>
      <section class="news-grid">{"".join(cards)}</section>
      <section class="health">
        <h2>Source health</h2>
        {health_detail}
      </section>
    </main>
    <footer>Generated by Airline Watch. Headlines link to the original source.</footer>
  </div>
  <script>
    document.querySelectorAll(".filter").forEach(button => {{
      button.addEventListener("click", () => {{
        document.querySelectorAll(".filter").forEach(item => item.classList.remove("active"));
        button.classList.add("active");
        const selected = button.dataset.filter;
        document.querySelectorAll(".news-card").forEach(card => {{
          card.style.display = selected === "all" || card.dataset.category === selected
            ? "" : "none";
        }});
      }});
    }});
  </script>
</body>
</html>
"""
