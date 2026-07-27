# Phase 0 Probe

## Goal

Generate three judgment-ready country cards for:

- `US`
- `JP`
- `BR`

The script collects:

- recent country-specific Google News top stories
- recent Google Trends candidates
- recent Wikipedia pageview candidates
- hard-filtered shortlists from a pluggable filter pipeline
- optional AI summaries and explanations through OpenAI

## Requirements

- Python 3.12+
- network access
- `OPENAI_API_KEY` for full runs, or a local `key.txt`

`requests` is already available in the current environment.

## Commands

Dry run without OpenAI:

```bash
python3 scripts/probe.py --dry-run --stdout
```

Full run with OpenAI:

```bash
export OPENAI_API_KEY=...
python3 scripts/probe.py --stdout
```

Or place the key in `key.txt` at the project root and run:

```bash
python3 scripts/probe.py --stdout
```

Run one country only:

```bash
python3 scripts/probe.py --country JP --dry-run --stdout
```

## Output

The script writes:

- `outputs/phase0/probe-results.json`
- `outputs/phase0/US.json`
- `outputs/phase0/JP.json`
- `outputs/phase0/BR.json`

Each card contains:

- `top_news`
- `meme`
- `keywords`
- `raw_candidates`
- `fetch_diagnostics.news.filters`
- `fetch_diagnostics.trends.filters`
- `probe_status`

## Notes

- `--dry-run` skips OpenAI and keeps only fetched candidates.
- The default model is `gpt-4.1-mini`, override with `--model` or `OPENAI_MODEL`.
- `key.txt` can contain either the raw key or `OPENAI_API_KEY=...`.
- Reddit has been removed from the Phase 0 probe path.
- `top_news` and `meme` are now separate source pipelines.
- `meme` candidates come from non-news-native sources first, currently `Google Trends` plus `Wikipedia pageviews`.
- `Wikipedia pageviews` is enabled selectively; it is disabled for countries where the language wiki is too global to feel country-specific, such as `US/en`.
- Candidate selection now uses a pluggable hard-filter pipeline before AI summarization.
- If one source is thin for a country, the output is still written with partial data.
