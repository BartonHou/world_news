# World Signals

An interactive world map showing what each country is talking, laughing, and
arguing about today — one top news story plus real internet culture (Reddit +
YouTube) per country, summarized by an LLM. Zero-backend static prototype.

Live map: _(set after enabling GitHub Pages — see below)_

## How it works

```
scripts/probe.py           # fetch signals (Google News RSS, Reddit .rss,
                           #   YouTube trending) -> filter -> LLM cards
scripts/export_phase1_data.py  # normalize into public/data/*.json
index.html + public/       # static frontend, reads public/data/*.json
```

- Meme layer = Reddit country/culture subreddits + YouTube region trending,
  balanced by a per-source quota.
- News layer = Google News top stories, summarized.
- Hover never calls an API — the frontend only reads pre-generated JSON.

## Run locally

```bash
pip install -r requirements.txt

# 1) generate data (needs API keys, ~15 min for all 20 countries)
python scripts/probe.py --output-dir outputs/phase0
python scripts/export_phase1_data.py

# 2) serve
python -m http.server 8766   # open http://127.0.0.1:8766/
```

Faster iterations: `--country US --country JP` to limit countries, `--dry-run`
to skip the LLM.

## API keys

Provided via environment variables (or local `key.txt` / `youtube_key.txt`,
both gitignored):

- `OPENAI_API_KEY` — news/meme summarization
- `YOUTUBE_API_KEY` — YouTube Data API v3 (free quota)

## Deployment (GitHub Actions + Pages)

`.github/workflows/deploy.yml` refreshes the data on a 12-hour schedule and
deploys the static site to GitHub Pages.

One-time setup:

1. Push this repo to GitHub.
2. Settings → Secrets and variables → Actions → add `OPENAI_API_KEY` and
   `YOUTUBE_API_KEY`.
3. Settings → Pages → Source = **GitHub Actions**.
4. Actions tab → run **Refresh data and deploy to Pages** once (or wait for the
   schedule).

Note: Reddit rate-limits/blocks datacenter IPs, so the meme layer may lose its
Reddit half when refreshed from GitHub runners (it falls back to YouTube + news
gracefully). For full-quality Reddit data, refresh locally and commit, or run
the refresh from a residential IP.
