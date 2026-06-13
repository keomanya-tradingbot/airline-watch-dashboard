# Airline Watch

Airline Watch monitors official aviation sources, airline product pages, and
news feeds for meaningful industry changes. It classifies findings into:

- policy and regulation
- fleet and aircraft
- leadership
- mobile app changes
- website changes
- operations and routes
- safety
- customer experience
- financial and strategic changes

The monitor preserves source URLs, suppresses duplicate observations, and
produces a Markdown digest. Website monitoring is snapshot-based, so it can
detect changes that never become news articles.

## Quick start

From this project directory:

```bash
./scripts/monitor.sh
```

This checks every configured source and writes the latest seven-day report to
`outputs/latest-digest.md`. It also builds a clean browser dashboard at
`outputs/dashboard.html`.

The first run establishes baselines for monitored web pages and apps. Later
runs report meaningful changes. To view results immediately:

```bash
cat outputs/latest-digest.md
```

Open `outputs/dashboard.html` in a browser to use the dashboard. It is a static
file, so there is no hosting bill and no server to keep running.

Outside Codex on the same computer, open this file directly in Chrome, Edge, or
Firefox:

`C:\Users\AI-Agent\Documents\Codex\2026-06-12\can-we-build-an-agent-that\outputs\dashboard.html`

You can also double-click `scripts\open_dashboard.cmd`.

Or serve it at a normal local web address:

```bash
./scripts/serve_dashboard.sh
```

Then visit `http://localhost:8765`. Keep that terminal running while using the
local web address. To access the dashboard from anywhere, publish the `outputs`
folder to a static host such as GitHub Pages, Cloudflare Pages, or Netlify.

## GitHub Pages

The included `.github/workflows/pages.yml` workflow refreshes the news and
publishes `outputs/` to GitHub Pages every morning. It can also be run manually
from the repository's Actions tab.

The workflow uses the local keyword summarizer by default, which has no API
cost. To enable model-generated summaries, add an `OPENAI_API_KEY` repository
secret. GitHub Pages must use **GitHub Actions** as its build and deployment
source.

You can also use the CLI directly:

```bash
.venv/bin/airline-watch run
.venv/bin/airline-watch digest --hours 168 \
  --output outputs/latest-digest.md
```

Set `OPENAI_API_KEY` to use structured model classification and summarization.
The default model can be changed with `AIRLINE_WATCH_MODEL`.

```bash
export OPENAI_API_KEY="..."
export AIRLINE_WATCH_MODEL="gpt-5.5"
airline-watch run --digest
```

Without an API key, the monitor uses a local keyword classifier and still
collects, stores, diffs, and reports findings.

## Configuration

Edit `config/sources.yaml`. A source is either:

- `feed`: RSS or Atom entries become observations.
- `news_page`: current newsroom articles are imported and deduplicated by URL.
- `page`: the visible page text is snapshotted and compared with the prior run.
- `app_store`: stable Apple release metadata is compared between runs.

Use `tier` to distinguish `regulator`, `official`, `industry`, and `media`
sources. This gives readers context about whether a change is confirmed by the
organization involved.

## Scheduling

The project does not monitor continuously until it is scheduled. Run collection
hourly and refresh the report after each check:

```cron
15 * * * * cd /path/to/project && ./scripts/monitor.sh
```

For production, send the generated Markdown to email, Slack, Teams, or a
database-backed dashboard. Keep urgent policy and safety alerts separate from
the daily digest.

## Project layout

- `config/sources.yaml`: websites, regulators, manufacturers, and apps watched
- `scripts/monitor.sh`: collect changes and refresh the readable digest
- `scripts/show_updates.sh`: display the latest digest in the terminal
- `scripts/serve_dashboard.sh`: serve the dashboard at `localhost:8765`
- `scripts/open_dashboard.cmd`: open the dashboard in your Windows browser
- `src/airline_watch/`: collector, analyzer, database, and report code
- `data/airline_watch.db`: saved baselines and observation history
- `outputs/latest-digest.md`: the report you read
- `outputs/dashboard.html`: filterable browser dashboard
