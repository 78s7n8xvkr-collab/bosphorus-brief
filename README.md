# The Bosphorus Brief

*Two continents. One briefing.*

A self-refreshing, static news briefing for internationals living in Türkiye
and the wider region. One page, checked over morning çay: curated headlines
across five sections, an AI-written daily digest, live lira rates, and
travel-advisory levels at a glance.

Everything is static files — no server, no database, no accounts, no
analytics, and the site is marked `noindex`. A scheduled GitHub Actions
workflow rebuilds the data every hour and redeploys the site to GitHub
Pages.

## What's inside

```
├── site/                  # the deployable site (open index.html to preview)
│   ├── index.html         # today's edition
│   ├── about.html         # mission, standards, sources
│   ├── assets/            # styles, client app, favicon
│   └── data/              # news.json, digest.json, rates.json (rebuilt hourly)
├── scripts/
│   ├── feeds.py           # source list — edit this to tune coverage
│   ├── fetch_news.py      # RSS aggregation + advisories + FX rates
│   └── generate_digest.py # Morning Çay (AI digest, with offline fallback)
└── .github/workflows/refresh.yml
```

The checked-in `site/data/` files are a seeded opening edition, so the site
renders meaningfully before the first automated refresh replaces them.

## Sections

- **Top Stories** — a scored, source-diverse mix across all sections
- **Türkiye** — national news
- **Region** — the wider neighbourhood
- **Migration & Residency** — permits, visas, citizenship, policy changes
- **Safety** — quakes, advisories, security developments (calm by design)
- **Economy** — the lira, inflation, cost of living
- **Saved** — a private reading list, stored only in the browser

## Coverage lenses

Every classified source carries an ownership-based lens label (state /
pro-gov / opposition / indep / intl / official — curated in
`scripts/feeds.py`). The pipeline clusters the same event across outlets
into one story with a coverage spectrum bar and an expandable source list,
and marks multi-source stories reported from only one side of the spectrum
as **one-lens coverage**. The daily digest reads the same lens tags and
notes when framing diverges between them. Labels describe ownership and
affiliation, which are public record — not article quality.

## How the refresh works

`.github/workflows/refresh.yml` runs hourly (plus on manual dispatch and on
pushes to `main`):

1. `fetch_news.py` pulls every source in `feeds.py`, dedupes, drops stale
   items, scores a Top Stories mix, parses U.S. State Department advisory
   levels, and fetches mid-market TRY rates. Any source may fail without
   breaking the run; if *everything* fails, the previous data is kept.
2. `generate_digest.py` brews **Morning Çay** once per İstanbul day. With an
   `ANTHROPIC_API_KEY` repository secret it's written by a Claude model
   (override the model with a `DIGEST_MODEL` repository variable); without
   one it falls back to an automated headline roundup.
3. The site deploys to GitHub Pages.

## Setup

1. In the repo settings → **Pages**, set the source to **GitHub Actions**
   (the workflow also attempts to enable this itself on first run).
2. Optional but recommended: add an `ANTHROPIC_API_KEY` secret
   (Settings → Secrets and variables → Actions) for the AI-written digest.
3. Run the **Refresh the Brief** workflow once by hand (Actions tab →
   Run workflow) if a deploy hasn't already run, and open the URL it prints.

To preview locally: `python3 -m http.server -d site` and open
`http://localhost:8000`.

A custom domain (Settings → Pages → Custom domain) gives the Brief a
cleaner address; otherwise it lives at
`<owner>.github.io/bosphorus-brief/`.

## Editorial voice

The Brief's copy — and the digest prompt in `generate_digest.py` — follows
one rule: plain, calm, professional language, useful to any international
resident. It reports on politics and religion when the news warrants, but
never attaches religious, ethnic, or political labels to individuals or
communities, and never dramatizes risk. Keep that voice when editing copy or
prompts; it's what makes the Brief worth reading in a crowded feed.

## Tuning coverage

All sources live in `scripts/feeds.py` — plain RSS/Atom URLs plus Google
News topic queries, each tagged with a section and an editorial weight. Add,
remove, or re-weight freely; the pipeline adapts. The advisory country list
and FX pairs are in the same file.
