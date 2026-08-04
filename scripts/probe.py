#!/usr/bin/env python3
"""Phase 0 probe for the world news + memes concept.

This script collects lightweight country signals from public sources and asks an
LLM to turn them into judgment-ready country cards.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote
import xml.etree.ElementTree as ET

import requests
from filter_config import (
    NEWS_FILTER_SPECS,
    NEWS_PATTERN_GROUPS,
    PERSON_NAME_BLOCKLIST,
    TREND_FILTER_SPECS,
    TREND_PATTERN_GROUPS,
)


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 "
    "world-news-phase0-probe/0.1"
)
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
DEFAULT_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Reddit throttles anonymous RSS hard (~20-30s between successful hits). We
# enforce a global minimum interval; LLM latency between countries counts
# toward it, so the real run pays little extra.
REDDIT_MIN_INTERVAL = float(os.getenv("REDDIT_MIN_INTERVAL", "25"))
_last_reddit_request = 0.0

# Reddit wants a unique, descriptive User-Agent for OAuth requests.
REDDIT_USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT", "python:world-signals:0.2 (by /u/worldsignals)"
)
_reddit_token: str | None = None
_reddit_token_tried = False


def reddit_throttle() -> None:
    global _last_reddit_request
    if _last_reddit_request:
        wait = REDDIT_MIN_INTERVAL - (time.monotonic() - _last_reddit_request)
        if wait > 0:
            time.sleep(wait)
    _last_reddit_request = time.monotonic()


@dataclass(frozen=True)
class CountryConfig:
    iso2: str
    country_name: str
    hl: str
    gl: str
    ceid: str
    wiki_project: str
    wiki_pageviews_enabled: bool = True
    # Country/culture subreddits — the real internet-culture signal. US has no
    # clean national culture sub, so it leans on US-dominated humor subs.
    subreddits: tuple[str, ...] = ()


@dataclass
class NewsCandidate:
    title: str
    source_name: str
    source_url: str
    published_at: str
    snippet: str
    short_explanation: str = ""


@dataclass
class TrendCandidate:
    title: str
    platform: str
    source_label: str
    score_label: str
    rank_score: int
    published_at: str
    source_url: str
    external_url: str
    context: str
    short_explanation: str = ""


@dataclass(frozen=True)
class FilterDecision:
    keep: bool = True
    score_delta: int = 0
    reason: str = ""


@dataclass(frozen=True)
class CandidateFilter:
    name: str
    fn: Callable[[CountryConfig, Any], FilterDecision | None]


COUNTRIES: dict[str, CountryConfig] = {
    "US": CountryConfig("US", "United States", "en-US", "US", "US:en", "en.wikipedia", False, ("AskAnAmerican", "memes")),
    "CA": CountryConfig("CA", "Canada", "en-CA", "CA", "CA:en", "en.wikipedia", False, ("canada", "onguardforthee")),
    "GB": CountryConfig("GB", "United Kingdom", "en-GB", "GB", "GB:en", "en.wikipedia", False, ("unitedkingdom", "CasualUK")),
    "FR": CountryConfig("FR", "France", "fr", "FR", "FR:fr", "fr.wikipedia", True, ("france",)),
    "DE": CountryConfig("DE", "Germany", "de", "DE", "DE:de", "de.wikipedia", True, ("de", "germany")),
    "JP": CountryConfig("JP", "Japan", "ja", "JP", "JP:ja", "ja.wikipedia", True, ("newsokur", "japan")),
    "KR": CountryConfig("KR", "South Korea", "ko", "KR", "KR:ko", "ko.wikipedia", True, ("hanguk", "korea")),
    "CN": CountryConfig("CN", "China", "zh-CN", "CN", "CN:zh-Hans", "zh.wikipedia", True, ("China", "China_irl")),
    "IN": CountryConfig("IN", "India", "en-IN", "IN", "IN:en", "en.wikipedia", False, ("india", "IndiaSpeaks")),
    "BR": CountryConfig("BR", "Brazil", "pt-BR", "BR", "BR:pt-419", "pt.wikipedia", True, ("brasil",)),
    "MX": CountryConfig("MX", "Mexico", "es-419", "MX", "MX:es-419", "es.wikipedia", True, ("mexico",)),
    "AR": CountryConfig("AR", "Argentina", "es-419", "AR", "AR:es-419", "es.wikipedia", True, ("argentina",)),
    "AU": CountryConfig("AU", "Australia", "en-AU", "AU", "AU:en", "en.wikipedia", False, ("australia",)),
    "RU": CountryConfig("RU", "Russia", "ru", "RU", "RU:ru", "ru.wikipedia", True, ("AskARussian", "russia")),
    "UA": CountryConfig("UA", "Ukraine", "uk", "UA", "UA:uk", "uk.wikipedia", True, ("ukraine",)),
    "TR": CountryConfig("TR", "Turkey", "tr", "TR", "TR:tr", "tr.wikipedia", True, ("Turkey", "TurkeyJerky")),
    "ID": CountryConfig("ID", "Indonesia", "id", "ID", "ID:id", "id.wikipedia", True, ("indonesia",)),
    "PH": CountryConfig("PH", "Philippines", "en-PH", "PH", "PH:en", "en.wikipedia", False, ("Philippines",)),
    "ZA": CountryConfig("ZA", "South Africa", "en-ZA", "ZA", "ZA:en", "en.wikipedia", False, ("southafrica",)),
    "NG": CountryConfig("NG", "Nigeria", "en-NG", "NG", "NG:en", "en.wikipedia", False, ("Nigeria",)),
    "IT": CountryConfig("IT", "Italy", "it", "IT", "IT:it", "it.wikipedia", True, ("italy",)),
    "ES": CountryConfig("ES", "Spain", "es", "ES", "ES:es", "es.wikipedia", True, ("es", "spain")),
    "NL": CountryConfig("NL", "Netherlands", "nl", "NL", "NL:nl", "nl.wikipedia", True, ("thenetherlands",)),
    "PL": CountryConfig("PL", "Poland", "pl", "PL", "PL:pl", "pl.wikipedia", True, ("Polska",)),
    "SE": CountryConfig("SE", "Sweden", "sv", "SE", "SE:sv", "sv.wikipedia", True, ("sweden",)),
    "PT": CountryConfig("PT", "Portugal", "pt-PT", "PT", "PT:pt-150", "pt.wikipedia", True, ("portugal",)),
    "TH": CountryConfig("TH", "Thailand", "th", "TH", "TH:th", "th.wikipedia", True, ("Thailand",)),
    "VN": CountryConfig("VN", "Vietnam", "vi", "VN", "VN:vi", "vi.wikipedia", True, ("VietNam",)),
    "MY": CountryConfig("MY", "Malaysia", "en-MY", "MY", "MY:en", "en.wikipedia", False, ("malaysia",)),
    "PK": CountryConfig("PK", "Pakistan", "en-PK", "PK", "PK:en", "en.wikipedia", False, ("pakistan",)),
    "EG": CountryConfig("EG", "Egypt", "ar", "EG", "EG:ar", "ar.wikipedia", True, ("Egypt",)),
    "IL": CountryConfig("IL", "Israel", "he", "IL", "IL:he", "he.wikipedia", True, ("Israel",)),
    "SA": CountryConfig("SA", "Saudi Arabia", "ar", "SA", "SA:ar", "ar.wikipedia", True, ("saudiarabia",)),
    "KE": CountryConfig("KE", "Kenya", "en-KE", "KE", "KE:en", "en.wikipedia", False, ("Kenya",)),
    "CO": CountryConfig("CO", "Colombia", "es-419", "CO", "CO:es-419", "es.wikipedia", True, ("Colombia",)),
    "CL": CountryConfig("CL", "Chile", "es-419", "CL", "CL:es-419", "es.wikipedia", True, ("chile",)),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Phase 0 country-card probe for US, JP, and BR."
    )
    parser.add_argument(
        "--country",
        dest="countries",
        action="append",
        choices=sorted(COUNTRIES),
        help="Repeat to limit the run to selected countries. Defaults to all.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/phase0",
        help="Directory where JSON outputs will be written.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="OpenAI model name. Defaults to OPENAI_MODEL or gpt-4.1-mini.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--news-limit",
        type=int,
        default=5,
        help="How many news candidates to keep per country.",
    )
    parser.add_argument(
        "--trend-limit",
        type=int,
        default=8,
        help="How many trend candidates to keep per country.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip OpenAI calls and output candidate-only cards.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the final combined JSON to stdout.",
    )
    return parser.parse_args()


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_google_news_url(config: CountryConfig) -> str:
    return f"https://news.google.com/rss?hl={config.hl}&gl={config.gl}&ceid={config.ceid}"


def strip_html(raw_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def request_text(url: str, timeout: float) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
            "User-Agent": USER_AGENT,
        },
    )
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response.text


def request_json(url: str, timeout: float) -> dict[str, Any]:
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    response.raise_for_status()
    return response.json()


def fetch_news_candidates(
    config: CountryConfig, limit: int, timeout: float
) -> tuple[list[NewsCandidate], dict[str, Any]]:
    source_url = build_google_news_url(config)
    xml_text = request_text(source_url, timeout=timeout)
    root = ET.fromstring(xml_text)
    items = root.findall("./channel/item")
    candidates: list[NewsCandidate] = []
    seen: set[str] = set()

    raw_limit = max(limit * 4, 12)
    for item in items:
        title_text = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        snippet = strip_html(item.findtext("description") or "")
        source_name = ""

        source_node = item.find("source")
        if source_node is not None and source_node.text:
            source_name = source_node.text.strip()
        elif " - " in title_text:
            title_text, source_name = title_text.rsplit(" - ", 1)

        dedupe_key = normalize_key(title_text)
        if not title_text or dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        candidates.append(
            NewsCandidate(
                title=title_text,
                source_name=source_name or "Unknown source",
                source_url=link,
                published_at=pub_date,
                snippet=snippet,
            )
        )
        if len(candidates) >= raw_limit:
            break

    diagnostic = {
        "source": "google_news_top_rss",
        "url": source_url,
        "items_seen": len(items),
        "items_kept": len(candidates),
    }
    return candidates, diagnostic


def fetch_google_trends_candidates(
    config: CountryConfig, limit: int, timeout: float
) -> tuple[list[TrendCandidate], dict[str, Any]]:
    source_url = f"https://trends.google.com/trending/rss?geo={config.iso2}"
    xml_text = request_text(source_url, timeout=timeout)
    root = ET.fromstring(xml_text)
    namespaces = {"ht": "https://trends.google.com/trending/rss"}
    items = root.findall("./channel/item")
    candidates: list[TrendCandidate] = []
    seen: set[str] = set()

    raw_limit = max(limit * 2, 10)
    for item in items:
        title = (item.findtext("title") or "").strip()
        if not title:
            continue

        dedupe_key = normalize_key(title)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        traffic = (item.findtext("ht:approx_traffic", namespaces=namespaces) or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source_label = (
            item.findtext("ht:picture_source", namespaces=namespaces) or "Google Trends"
        ).strip()
        news_title = (
            item.findtext("ht:news_item/ht:news_item_title", namespaces=namespaces) or ""
        ).strip()
        news_snippet = (
            item.findtext("ht:news_item/ht:news_item_snippet", namespaces=namespaces) or ""
        ).strip()
        news_url = (
            item.findtext("ht:news_item/ht:news_item_url", namespaces=namespaces) or ""
        ).strip()
        context = " ".join(part for part in [news_title, news_snippet] if part).strip()

        candidates.append(
            TrendCandidate(
                title=title,
                platform="google_trends",
                source_label=source_label,
                score_label=traffic or "traffic unavailable",
                rank_score=parse_traffic_score(traffic),
                published_at=pub_date,
                source_url=source_url,
                external_url=news_url or source_url,
                context=context,
            )
        )
        if len(candidates) >= raw_limit:
            break

    diagnostic = {
        "source": "google_trends_rss",
        "url": source_url,
        "items_seen": len(items),
        "items_kept": len(candidates),
    }
    return candidates, diagnostic


def build_wikipedia_top_url(config: CountryConfig, day: datetime) -> str:
    return (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
        f"{config.wiki_project}/all-access/{day:%Y/%m/%d}"
    )


def build_wikipedia_summary_url(config: CountryConfig, article: str) -> str:
    page_title = quote(article.replace(" ", "_"), safe="")
    return f"https://{config.wiki_project}.org/api/rest_v1/page/summary/{page_title}"


def is_valid_wikipedia_article(article: str) -> bool:
    title = article.strip()
    if not title or title in {
        "Main_Page",
        "Main Page",
        "メインページ",
        "Página_principal",
        "Página principal",
        "-",
    }:
        return False
    if re.fullmatch(r"\d{4}", title):
        return False
    if re.fullmatch(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)_\d{1,2}",
        title,
        flags=re.IGNORECASE,
    ):
        return False
    if re.fullmatch(r"\d{1,2}_de_[A-Za-zçÇ]+", title):
        return False
    if re.fullmatch(r"\d+月\d+日", title):
        return False
    blocked_prefixes = (
        "Special:",
        "Template:",
        "File:",
        "Portal:",
        "Wikipedia:",
        "Help:",
        "Category:",
        "Talk:",
        "Especial:",
        "Predefinição:",
        "Ajuda:",
        "Categoria:",
        "特別:",
        "テンプレート:",
        "ファイル:",
        "ポータル:",
        "ヘルプ:",
        "カテゴリ:",
        "ノート:",
    )
    return not title.startswith(blocked_prefixes)


def fetch_wikipedia_summary(
    config: CountryConfig,
    article: str,
    timeout: float,
) -> tuple[str, str]:
    url = build_wikipedia_summary_url(config, article)
    payload = request_json(url, timeout=timeout)
    summary = (payload.get("extract") or "").strip()
    external_url = (
        payload.get("content_urls", {})
        .get("desktop", {})
        .get("page", "")
        .strip()
    )
    return summary, external_url or url


def fetch_wikipedia_pageview_candidates(
    config: CountryConfig,
    limit: int,
    timeout: float,
) -> tuple[list[TrendCandidate], dict[str, Any]]:
    candidates: list[TrendCandidate] = []
    seen: set[str] = set()
    raw_limit = max(limit, 6)
    last_error = ""

    for days_back in (1, 2, 3):
        day = datetime.now(timezone.utc) - timedelta(days=days_back)
        source_url = build_wikipedia_top_url(config, day)
        try:
            payload = request_json(source_url, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            continue

        items = payload.get("items") or []
        if not items:
            last_error = "wikimedia top endpoint returned no items"
            continue

        articles = items[0].get("articles") or []
        for article in articles:
            raw_title = str(article.get("article") or "").strip()
            if not is_valid_wikipedia_article(raw_title):
                continue

            title = raw_title.replace("_", " ")
            dedupe_key = normalize_key(title)
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            views = int(article.get("views") or 0)
            rank = int(article.get("rank") or 0)
            try:
                summary, external_url = fetch_wikipedia_summary(config, title, timeout)
            except Exception:
                summary = ""
                external_url = f"https://{config.wiki_project}.org/wiki/{quote(raw_title, safe='')}"

            candidates.append(
                TrendCandidate(
                    title=title,
                    platform="wikipedia_pageviews",
                    source_label=f"{config.wiki_project} daily pageviews",
                    score_label=f"{views} views (rank #{rank})" if views else f"rank #{rank}",
                    rank_score=views,
                    published_at=day.replace(
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0,
                    ).isoformat(),
                    source_url=source_url,
                    external_url=external_url,
                    context=summary,
                )
            )
            if len(candidates) >= raw_limit:
                break

        diagnostic = {
            "source": "wikimedia_pageviews_top",
            "url": source_url,
            "data_date": day.strftime("%Y-%m-%d"),
            "items_seen": len(articles),
            "items_kept": len(candidates),
        }
        if candidates:
            return candidates, diagnostic

    diagnostic = {
        "source": "wikimedia_pageviews_top",
        "status": "error",
        "message": last_error or "no valid wikipedia pageview candidates",
    }
    return [], diagnostic


def dedupe_trend_candidates(candidates: list[TrendCandidate]) -> list[TrendCandidate]:
    merged: dict[str, TrendCandidate] = {}

    for candidate in candidates:
        key = normalize_key(candidate.title)
        if not key:
            continue
        existing = merged.get(key)
        if existing is None:
            merged[key] = candidate
            continue

        preferred = existing
        if candidate.platform == "wikipedia_pageviews" and existing.platform != "wikipedia_pageviews":
            preferred = candidate
        elif len(candidate.context) > len(existing.context):
            preferred = candidate
        elif candidate.rank_score > existing.rank_score:
            preferred = candidate

        merged[key] = preferred

    return list(merged.values())


def load_youtube_api_key() -> str | None:
    env_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if env_key:
        return env_key.strip()
    for path in [Path.cwd() / "youtube_key.txt", PROJECT_ROOT / "youtube_key.txt"]:
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                first = text.splitlines()[0].strip()
                if "=" in first:
                    return first.split("=", 1)[1].strip()
                return first
    return None


def load_reddit_credentials() -> tuple[str, str] | None:
    """Read-only Reddit app credentials (client_id, client_secret) from env or a
    reddit_key.txt file (two lines, or `id:secret`)."""
    cid = os.getenv("REDDIT_CLIENT_ID")
    csec = os.getenv("REDDIT_CLIENT_SECRET")
    if cid and csec:
        return cid.strip(), csec.strip()
    for path in [Path.cwd() / "reddit_key.txt", PROJECT_ROOT / "reddit_key.txt"]:
        if not path.exists():
            continue
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(lines) >= 2:
            return lines[0], lines[1]
        if len(lines) == 1 and ":" in lines[0]:
            cid, csec = lines[0].split(":", 1)
            return cid.strip(), csec.strip()
    return None


def get_reddit_token(client_id: str, client_secret: str, timeout: float) -> str | None:
    """App-only OAuth token (client_credentials grant). Cached for the run.
    Authenticated requests aren't IP-blocked like anonymous ones, so this is
    what lets a datacenter/CI runner read Reddit reliably."""
    global _reddit_token, _reddit_token_tried
    if _reddit_token or _reddit_token_tried:
        return _reddit_token
    _reddit_token_tried = True
    try:
        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": REDDIT_USER_AGENT},
            timeout=timeout,
        )
        response.raise_for_status()
        _reddit_token = response.json().get("access_token")
    except Exception as exc:  # noqa: BLE001
        print(f"[probe] reddit oauth token failed: {exc}", file=sys.stderr)
        _reddit_token = None
    return _reddit_token


def fetch_reddit_via_oauth(
    config: CountryConfig,
    limit: int,
    timeout: float,
    token: str,
) -> tuple[list[TrendCandidate], dict[str, Any]]:
    """Authenticated JSON listing via oauth.reddit.com. Richer than RSS (score,
    stickied flag) and not IP-blocked, so it works from CI."""
    candidates: list[TrendCandidate] = []
    seen: set[str] = set()
    per_sub_diag: list[dict[str, Any]] = []
    headers = {"Authorization": f"Bearer {token}", "User-Agent": REDDIT_USER_AGENT}

    for sub in config.subreddits:
        if len(candidates) >= limit:
            break
        time.sleep(0.6)  # polite; OAuth allows ~100 requests/minute
        url = f"https://oauth.reddit.com/r/{sub}/hot?limit=25&raw_json=1"
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            children = response.json().get("data", {}).get("children", [])
        except Exception as exc:  # noqa: BLE001
            per_sub_diag.append({"subreddit": sub, "status": "error", "message": str(exc)})
            continue

        kept = 0
        for rank, child in enumerate(children):
            data = child.get("data", {})
            if data.get("stickied"):
                continue  # skip pinned mod/announcement posts (precise here)
            title = (data.get("title") or "").strip()
            if not title:
                continue
            dedupe_key = normalize_key(title)
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            permalink = data.get("permalink") or ""
            post_url = f"https://www.reddit.com{permalink}" if permalink else ""
            external = (data.get("url") or "").strip()
            candidates.append(
                TrendCandidate(
                    title=title,
                    platform="reddit",
                    source_label=f"r/{sub}",
                    score_label=f"r/{sub} · {data.get('score', 0)} upvotes",
                    rank_score=max(0, 1000 - rank * 10),
                    published_at=utc_from_timestamp(data.get("created_utc") or 0),
                    source_url=post_url or external,
                    external_url=external or post_url,
                    context=strip_html(data.get("selftext") or "")[:400],
                )
            )
            kept += 1
        per_sub_diag.append({"subreddit": sub, "status": "ok", "items_kept": kept})

    diagnostic = {"source": "reddit_oauth", "subreddits": per_sub_diag, "items_kept": len(candidates)}
    return candidates, diagnostic


def fetch_reddit_candidates(
    config: CountryConfig,
    limit: int,
    timeout: float,
) -> tuple[list[TrendCandidate], dict[str, Any]]:
    """Country/culture subreddit hot posts. Uses authenticated OAuth if
    credentials are available (works from CI/datacenter IPs); otherwise falls
    back to the anonymous .rss feed (fine on residential IPs, may 403 in CI)."""
    if not config.subreddits:
        return [], {"source": "reddit", "status": "disabled", "message": "no subreddits configured"}

    creds = load_reddit_credentials()
    if creds:
        token = get_reddit_token(creds[0], creds[1], timeout)
        if token:
            return fetch_reddit_via_oauth(config, limit, timeout, token)

    return fetch_reddit_via_rss(config, limit, timeout)


def fetch_reddit_via_rss(
    config: CountryConfig,
    limit: int,
    timeout: float,
) -> tuple[list[TrendCandidate], dict[str, Any]]:
    """Anonymous fallback: the .rss feed (the .json API is 403 for anonymous
    clients). Rate-limited, so we throttle between subs and back off on 429."""
    atom = {"a": "http://www.w3.org/2005/Atom"}
    candidates: list[TrendCandidate] = []
    seen: set[str] = set()
    per_sub_diag: list[dict[str, Any]] = []

    backoffs = [3.0, 6.0, 10.0]  # Reddit 429s aggressively on anonymous RSS
    for sub_index, sub in enumerate(config.subreddits):
        # Stop once one subreddit already gave us enough — fewer requests, less throttling.
        if len(candidates) >= limit:
            break
        source_url = f"https://www.reddit.com/r/{sub}/hot.rss?limit=25"
        text = ""
        status = 0
        for attempt in range(3):
            try:
                reddit_throttle()
                response = requests.get(
                    source_url,
                    timeout=timeout,
                    headers={"Accept": "application/atom+xml, */*", "User-Agent": USER_AGENT},
                )
                status = response.status_code
                if status == 429 and attempt < len(backoffs) - 1:
                    time.sleep(backoffs[attempt])
                    continue
                response.raise_for_status()
                text = response.text
                break
            except Exception as exc:  # noqa: BLE001
                per_sub_diag.append({"subreddit": sub, "status": "error", "message": str(exc)})
                text = ""
                break

        if not text:
            continue

        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            per_sub_diag.append({"subreddit": sub, "status": "parse_error", "message": str(exc)})
            continue

        entries = root.findall(".//a:entry", atom)
        kept = 0
        for rank, entry in enumerate(entries):
            title = (entry.findtext("a:title", namespaces=atom) or "").strip()
            if not title:
                continue
            link_node = entry.find("a:link", atom)
            link = link_node.get("href").strip() if link_node is not None and link_node.get("href") else ""
            content = strip_html(entry.findtext("a:content", namespaces=atom) or "")
            dedupe_key = normalize_key(title)
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            candidates.append(
                TrendCandidate(
                    title=title,
                    platform="reddit",
                    source_label=f"r/{sub}",
                    score_label=f"r/{sub} hot #{rank + 1}",
                    rank_score=max(0, 1000 - rank * 10),
                    published_at=(entry.findtext("a:updated", namespaces=atom) or "").strip(),
                    source_url=link or source_url,
                    external_url=link or source_url,
                    context=content[:400],
                )
            )
            kept += 1
        per_sub_diag.append({"subreddit": sub, "status": status or "ok", "items_kept": kept})

    diagnostic = {"source": "reddit_rss", "subreddits": per_sub_diag, "items_kept": len(candidates)}
    return candidates, diagnostic


def fetch_youtube_candidates(
    config: CountryConfig,
    limit: int,
    timeout: float,
) -> tuple[list[TrendCandidate], dict[str, Any]]:
    """Region trending videos (music, creators, viral clips) via YouTube Data
    API. Dormant until a YOUTUBE_API_KEY / youtube_key.txt is provided."""
    api_key = load_youtube_api_key()
    if not api_key:
        return [], {"source": "youtube_trending", "status": "disabled", "message": "no YOUTUBE_API_KEY"}

    source_url = (
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet&chart=mostPopular&regionCode={config.iso2}"
        f"&maxResults={max(limit, 10)}&key={api_key}"
    )
    try:
        payload = request_json(source_url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return [], {"source": "youtube_trending", "status": "error", "message": str(exc)}

    candidates: list[TrendCandidate] = []
    seen: set[str] = set()
    items = payload.get("items") or []
    for rank, item in enumerate(items):
        snippet = item.get("snippet") or {}
        title = (snippet.get("title") or "").strip()
        video_id = item.get("id") or ""
        if not title or not video_id:
            continue
        dedupe_key = normalize_key(title)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        channel = (snippet.get("channelTitle") or "").strip()
        description = (snippet.get("description") or "").strip()
        candidates.append(
            TrendCandidate(
                title=title,
                platform="youtube",
                source_label=f"YouTube trending ({channel})" if channel else "YouTube trending",
                score_label=f"trending #{rank + 1}",
                rank_score=max(0, 1000 - rank * 10),
                published_at=(snippet.get("publishedAt") or "").strip(),
                source_url=f"https://www.youtube.com/watch?v={video_id}",
                external_url=f"https://www.youtube.com/watch?v={video_id}",
                context=f"{channel}. {description}"[:400].strip(),
            )
        )

    return candidates, {"source": "youtube_trending", "url": "youtube.data.api", "items_kept": len(candidates)}


def fetch_meme_candidates(
    config: CountryConfig,
    limit: int,
    timeout: float,
) -> tuple[list[TrendCandidate], dict[str, Any]]:
    diagnostics: dict[str, Any] = {}
    collected: list[TrendCandidate] = []

    # Reddit first — the real internet-culture signal.
    try:
        reddit_candidates, diagnostics["reddit"] = fetch_reddit_candidates(config, limit=limit, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        reddit_candidates = []
        diagnostics["reddit"] = {"source": "reddit_rss", "status": "error", "message": str(exc)}
        print(f"[probe] reddit fetch failed for {config.iso2}: {exc}", file=sys.stderr)
    collected.extend(reddit_candidates)

    # YouTube region trending (dormant without an API key).
    try:
        youtube_candidates, diagnostics["youtube"] = fetch_youtube_candidates(config, limit=limit, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        youtube_candidates = []
        diagnostics["youtube"] = {"source": "youtube_trending", "status": "error", "message": str(exc)}
        print(f"[probe] youtube fetch failed for {config.iso2}: {exc}", file=sys.stderr)
    collected.extend(youtube_candidates)

    try:
        google_trends_candidates, diagnostics["google_trends"] = fetch_google_trends_candidates(
            config,
            limit=limit,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001
        google_trends_candidates = []
        diagnostics["google_trends"] = {
            "source": "google_trends_rss",
            "status": "error",
            "message": str(exc),
        }
        print(
            f"[probe] google trends fetch failed for {config.iso2}: {exc}",
            file=sys.stderr,
        )
    collected.extend(google_trends_candidates)

    if config.wiki_pageviews_enabled:
        try:
            wikipedia_candidates, diagnostics["wikipedia_pageviews"] = fetch_wikipedia_pageview_candidates(
                config,
                limit=limit,
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001
            wikipedia_candidates = []
            diagnostics["wikipedia_pageviews"] = {
                "source": "wikimedia_pageviews_top",
                "status": "error",
                "message": str(exc),
            }
            print(
                f"[probe] wikipedia pageviews fetch failed for {config.iso2}: {exc}",
                file=sys.stderr,
            )
        collected.extend(wikipedia_candidates)
    else:
        diagnostics["wikipedia_pageviews"] = {
            "source": "wikimedia_pageviews_top",
            "status": "disabled",
            "message": "disabled for countries where language wiki is too global",
        }

    return dedupe_trend_candidates(collected), diagnostics


def utc_from_timestamp(timestamp: float) -> str:
    if not timestamp:
        return ""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat()


def normalize_key(value: str) -> str:
    return re.sub(r"\W+", "", value or "").lower()


def parse_traffic_score(value: str) -> int:
    digits = re.sub(r"[^\d]", "", value or "")
    if not digits:
        return 0
    return int(digits)


def build_news_filter_text(candidate: NewsCandidate) -> str:
    return " ".join(
        [
            candidate.title,
            candidate.snippet,
            candidate.source_name,
        ]
    )


def build_trend_filter_text(candidate: TrendCandidate) -> str:
    return " ".join(
        [
            candidate.title,
            candidate.context,
            candidate.source_label,
        ]
    )


def build_candidate_title_text(candidate: Any) -> str:
    return getattr(candidate, "title", "")


def build_candidate_context_text(candidate: Any) -> str:
    return getattr(candidate, "context", "")


def looks_like_bare_person_name(title: str) -> bool:
    normalized = title.strip()
    if not normalized:
        return False

    cjk_non_person_markers = (
        "騒動",
        "危機",
        "事件",
        "ドラマ",
        "映画",
        "台風",
        "速報",
        "銀行",
        "市場",
        "組",
        "対",
        "戦",
    )
    if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", normalized):
        if any(marker in normalized for marker in cjk_non_person_markers):
            return False
        return True

    if re.fullmatch(
        r"[A-Za-z][A-Za-z'.-]{1,20}( [A-Za-z][A-Za-z'.-]{1,20}){1,2}",
        normalized,
    ):
        return all(
            token.lower() not in PERSON_NAME_BLOCKLIST for token in normalized.split()
        )

    return False


def make_regex_filter(
    name: str,
    text_getter: Callable[[Any], str],
    patterns: list[str],
    *,
    score_delta: int = 0,
    drop: bool = False,
    unless_patterns: list[str] | None = None,
) -> CandidateFilter:
    def _fn(_: CountryConfig, candidate: Any) -> FilterDecision | None:
        text = text_getter(candidate)
        if unless_patterns and contains_any(text, unless_patterns):
            return None
        if not contains_any(text, patterns):
            return None
        return FilterDecision(
            keep=not drop,
            score_delta=score_delta,
            reason=name,
        )

    return CandidateFilter(name=name, fn=_fn)


def looks_local_to_country(config: CountryConfig, text: str) -> bool:
    if config.iso2 == "JP":
        return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text))
    if config.iso2 == "BR":
        lowered = text.lower()
        return any(
            marker in lowered
            for marker in [".br", "g1", "uol", "globo", "ge.globo", "cnn brasil", "estadão"]
        )
    return False


def make_local_signal_filter(
    name: str,
    text_getter: Callable[[Any], str],
    *,
    score_delta: int,
) -> CandidateFilter:
    def _fn(config: CountryConfig, candidate: Any) -> FilterDecision | None:
        extra = []
        source_url = getattr(candidate, "source_url", "")
        external_url = getattr(candidate, "external_url", "")
        if source_url:
            extra.append(source_url)
        if external_url:
            extra.append(external_url)
        haystack = " ".join([text_getter(candidate), *extra])
        if not looks_local_to_country(config, haystack):
            return None
        return FilterDecision(score_delta=score_delta, reason=name)

    return CandidateFilter(name=name, fn=_fn)


def make_thin_context_filter(name: str, *, score_delta: int) -> CandidateFilter:
    def _fn(_: CountryConfig, candidate: TrendCandidate) -> FilterDecision | None:
        if candidate.context.strip():
            return None
        return FilterDecision(score_delta=score_delta, reason=name)

    return CandidateFilter(name=name, fn=_fn)


def make_strong_traffic_filter(
    name: str,
    *,
    threshold: int,
    score_delta: int,
) -> CandidateFilter:
    def _fn(_: CountryConfig, candidate: TrendCandidate) -> FilterDecision | None:
        if candidate.rank_score < threshold:
            return None
        return FilterDecision(score_delta=score_delta, reason=name)

    return CandidateFilter(name=name, fn=_fn)


def make_bare_person_name_filter(
    name: str,
    *,
    score_delta: int,
) -> CandidateFilter:
    def _fn(_: CountryConfig, candidate: TrendCandidate) -> FilterDecision | None:
        if not looks_like_bare_person_name(candidate.title):
            return None
        return FilterDecision(score_delta=score_delta, reason=name)

    return CandidateFilter(name=name, fn=_fn)


def make_platform_filter(
    name: str,
    *,
    platforms: list[str],
    score_delta: int,
) -> CandidateFilter:
    allowed = set(platforms)

    def _fn(_: CountryConfig, candidate: TrendCandidate) -> FilterDecision | None:
        if candidate.platform not in allowed:
            return None
        return FilterDecision(score_delta=score_delta, reason=name)

    return CandidateFilter(name=name, fn=_fn)


def build_filters(
    specs: list[dict[str, Any]],
    pattern_groups: dict[str, list[str]],
    text_getter: Callable[[Any], str],
    *,
    title_getter: Callable[[Any], str] = build_candidate_title_text,
    context_getter: Callable[[Any], str] = build_candidate_context_text,
) -> list[CandidateFilter]:
    filters: list[CandidateFilter] = []

    for spec in specs:
        filter_type = spec["type"]
        name = spec["name"]
        score_delta = int(spec.get("score_delta", 0))

        if filter_type == "regex":
            pattern_group = spec["pattern_group"]
            unless_group = spec.get("unless_group")
            text_scope = spec.get("text_scope")
            if text_scope == "title":
                getter = title_getter
            elif text_scope == "context":
                getter = context_getter
            else:
                getter = text_getter
            filters.append(
                make_regex_filter(
                    name,
                    getter,
                    pattern_groups[pattern_group],
                    score_delta=score_delta,
                    drop=bool(spec.get("drop", False)),
                    unless_patterns=(
                        pattern_groups[unless_group] if unless_group else None
                    ),
                )
            )
            continue

        if filter_type == "local_signal":
            filters.append(
                make_local_signal_filter(
                    name,
                    text_getter,
                    score_delta=score_delta,
                )
            )
            continue

        if filter_type == "thin_context":
            filters.append(
                make_thin_context_filter(
                    name,
                    score_delta=score_delta,
                )
            )
            continue

        if filter_type == "strong_traffic":
            filters.append(
                make_strong_traffic_filter(
                    name,
                    threshold=int(spec["threshold"]),
                    score_delta=score_delta,
                )
            )
            continue

        if filter_type == "platform":
            filters.append(
                make_platform_filter(
                    name,
                    platforms=list(spec["platforms"]),
                    score_delta=score_delta,
                )
            )
            continue

        if filter_type == "bare_person_name":
            filters.append(
                make_bare_person_name_filter(
                    name,
                    score_delta=score_delta,
                )
            )
            continue

        raise ValueError(f"Unknown filter type: {filter_type}")

    return filters


def build_trend_ai_hint_prompt(
    country_name: str,
    candidates: list[TrendCandidate],
) -> str:
    payload = []
    for index, item in enumerate(candidates, start=1):
        payload.append(
            {
                "index": index,
                "title": item.title,
                "platform": item.platform,
                "source_label": item.source_label,
                "score_label": item.score_label,
                "published_at": item.published_at,
                "context": item.context,
            }
        )

    return (
        "You are helping a rule-based filter understand multilingual trend candidates.\n"
        "For each candidate, decide whether the raw title is too opaque, just a bare person name, or generic.\n"
        "Prefer candidates that feel like a native internet fixation or culture signal, not just a news headline with search spillover.\n"
        "If the context reveals a genuinely interesting story, provide a clearer English display title.\n"
        "Give a score_adjustment from -3 to 3 based on whether this candidate should move down or up for a global culture map.\n"
        "Return valid JSON only.\n"
        f"Country: {country_name}\n"
        f"Candidates: {json.dumps(payload, ensure_ascii=False)}\n"
        "Return:\n"
        "{\n"
        '  "hints": [\n'
        '    {"index": 1, "score_adjustment": 0, "normalized_title": "", "reason": ""}\n'
        "  ]\n"
        "}"
    )


def parse_trend_ai_hints(
    response: dict[str, Any],
    total_candidates: int,
) -> dict[int, dict[str, Any]]:
    hints = response.get("hints")
    parsed: dict[int, dict[str, Any]] = {}
    if not isinstance(hints, list):
        return parsed

    for item in hints:
        if not isinstance(item, dict):
            continue
        index = clamp_index(item.get("index"), total_candidates)
        try:
            score_adjustment = int(item.get("score_adjustment"))
        except (TypeError, ValueError):
            score_adjustment = 0
        normalized_title = item.get("normalized_title")
        if not isinstance(normalized_title, str):
            normalized_title = ""
        reason = item.get("reason")
        if not isinstance(reason, str):
            reason = ""
        parsed[index] = {
            "score_adjustment": max(-3, min(score_adjustment, 3)),
            "normalized_title": normalized_title.strip(),
            "reason": reason.strip(),
        }

    return parsed


NEWS_FILTERS = build_filters(
    NEWS_FILTER_SPECS,
    NEWS_PATTERN_GROUPS,
    build_news_filter_text,
)


TREND_FILTERS = build_filters(
    TREND_FILTER_SPECS,
    TREND_PATTERN_GROUPS,
    build_trend_filter_text,
)


def evaluate_filters(
    config: CountryConfig,
    candidate: Any,
    filters: list[CandidateFilter],
) -> tuple[bool, int, list[str]]:
    keep = True
    score = 0
    reasons: list[str] = []

    for candidate_filter in filters:
        decision = candidate_filter.fn(config, candidate)
        if decision is None:
            continue
        keep = keep and decision.keep
        score += decision.score_delta
        reasons.append(decision.reason or candidate_filter.name)

    return keep, score, reasons


def rank_news_candidates(
    config: CountryConfig,
    candidates: list[NewsCandidate],
    limit: int,
) -> tuple[list[NewsCandidate], list[dict[str, Any]]]:
    if not candidates:
        return [], []
    scored: list[tuple[bool, int, int, NewsCandidate, list[str]]] = []

    for index, candidate in enumerate(candidates):
        keep, score, reasons = evaluate_filters(config, candidate, NEWS_FILTERS)
        scored.append((keep, score, -index, candidate, reasons))

    scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    # Only candidates that passed the hard filters are eligible. The fallback
    # tops up from remaining *passing* candidates and never re-admits a dropped
    # one, so a hard drop (press release, etc.) stays dropped even when that
    # leaves fewer than `limit` candidates.
    shortlist = [item[3] for item in scored if item[0]][:limit]
    if len(shortlist) < limit:
        for keep, _, _, candidate, _ in scored:
            if not keep or candidate in shortlist:
                continue
            shortlist.append(candidate)
            if len(shortlist) >= limit:
                break

    kept_keys = {normalize_key(item.title) for item in shortlist}
    diagnostics = [
        {
            "title": candidate.title,
            "score": score,
            "reasons": reasons,
            "passed": keep,
            "kept": normalize_key(candidate.title) in kept_keys,
        }
        for keep, score, _, candidate, reasons in scored
    ]
    return shortlist, diagnostics


# Minimum shortlist slots reserved per culture source (if that many pass the
# hard filters). Keeps the feed a mix of Reddit discussion + YouTube watching
# instead of letting one source monopolize it. Sum must be <= trend limit.
TREND_SOURCE_QUOTAS = {"reddit": 3, "youtube": 3}


def apply_source_quota(
    passing: list[TrendCandidate],
    limit: int,
    quotas: dict[str, int],
) -> list[TrendCandidate]:
    """Pick `limit` candidates from ranked `passing`, guaranteeing each quota
    source a minimum count, then filling the rest by rank. Final order follows
    the original ranking so the best candidate still leads."""
    rank = {id(c): index for index, c in enumerate(passing)}
    chosen: list[TrendCandidate] = []
    chosen_ids: set[int] = set()

    for platform, need in quotas.items():
        taken = 0
        for candidate in passing:
            if taken >= need or len(chosen) >= limit:
                break
            if candidate.platform == platform and id(candidate) not in chosen_ids:
                chosen.append(candidate)
                chosen_ids.add(id(candidate))
                taken += 1

    for candidate in passing:
        if len(chosen) >= limit:
            break
        if id(candidate) not in chosen_ids:
            chosen.append(candidate)
            chosen_ids.add(id(candidate))

    chosen.sort(key=lambda candidate: rank[id(candidate)])
    return chosen[:limit]


def rank_trend_candidates(
    config: CountryConfig,
    candidates: list[TrendCandidate],
    limit: int,
    model: str,
    timeout: float,
    use_ai_assist: bool,
) -> tuple[list[TrendCandidate], list[dict[str, Any]]]:
    if not candidates:
        return [], []
    scored: list[tuple[bool, int, int, TrendCandidate, list[str]]] = []

    for candidate in candidates:
        keep, score, reasons = evaluate_filters(config, candidate, TREND_FILTERS)
        scored.append((keep, score, candidate.rank_score, candidate, reasons))

    scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)

    if use_ai_assist:
        review_count = min(len(scored), max(limit * 2, 6))
        review_slice = scored[:review_count]
        review_candidates = [item[3] for item in review_slice]
        try:
            hint_response = call_openai_json(
                build_trend_ai_hint_prompt(config.country_name, review_candidates),
                model=model,
                timeout=timeout,
            )
            hints = parse_trend_ai_hints(hint_response, len(review_candidates))
        except Exception:
            hints = {}

        rescored: list[tuple[bool, int, int, TrendCandidate, list[str]]] = []
        for idx, (keep, score, rank_score, candidate, reasons) in enumerate(scored, start=1):
            if idx <= review_count:
                hint = hints.get(idx)
                if hint:
                    score += int(hint["score_adjustment"])
                    if hint["reason"]:
                        reasons = [*reasons, f"ai:{hint['reason']}"]
                    normalized_title = hint.get("normalized_title") or ""
                    if normalized_title:
                        candidate = TrendCandidate(
                            title=normalized_title,
                            platform=candidate.platform,
                            source_label=candidate.source_label,
                            score_label=candidate.score_label,
                            rank_score=candidate.rank_score,
                            published_at=candidate.published_at,
                            source_url=candidate.source_url,
                            external_url=candidate.external_url,
                            context=candidate.context,
                        )
            rescored.append((keep, score, rank_score, candidate, reasons))
        scored = rescored
        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)

    # Passing = survived the hard filters (in ranked order). The source quota
    # then guarantees Reddit + YouTube each keep a minimum presence; hard-dropped
    # trends never enter because they are excluded from `passing`.
    passing = [item[3] for item in scored if item[0]]
    shortlist = apply_source_quota(passing, limit, TREND_SOURCE_QUOTAS)

    kept_keys = {normalize_key(item.title) for item in shortlist}
    diagnostics = [
        {
            "title": candidate.title,
            "score": score,
            "reasons": reasons,
            "passed": keep,
            "kept": normalize_key(candidate.title) in kept_keys,
        }
        for keep, score, _, candidate, reasons in scored
    ]
    return shortlist, diagnostics


def build_news_prompt(country_name: str, candidates: list[NewsCandidate]) -> str:
    articles = []
    for index, item in enumerate(candidates, start=1):
        articles.append(
            {
                "index": index,
                "headline": item.title,
                "source_name": item.source_name,
                "source_url": item.source_url,
                "published_at": item.published_at,
                "snippet": item.snippet,
            }
        )

    return (
        "You are selecting the most interesting country card for a global culture map.\n"
        "Given recent news headlines from one country, choose the story that is most "
        "worth showing to a curious outsider, not just the most institutionally important one.\n"
        "Rules:\n"
        "- Do not sensationalize. Do not invent facts.\n"
        "- Prefer the story that best reveals what people in this country may be talking, arguing, or fixating on.\n"
        "- Write for a global audience; explain local context when necessary.\n"
        "- Avoid routine election horse-race coverage, generic party infighting, ordinary crime, ordinary celebrity scandal, and ordinary game recaps unless they clearly signal something bigger or unusually revealing.\n"
        "- Avoid recurring annual or seasonal stories that feel like a predictable rerun unless this year's version has a genuinely new twist, conflict, or consequence.\n"
        "- Sports is only worth picking if it reflects a major milestone, national obsession, or broader cultural moment.\n"
        "- If every candidate is dull, choose the least dull one and lower confidence.\n"
        "- Keep 'summary' under 22 words and 'why_it_matters' under 16 words. Be tight, no filler.\n"
        "- Output valid JSON only.\n"
        f"Country: {country_name}\n"
        f"Articles: {json.dumps(articles, ensure_ascii=False)}\n"
        "Return:\n"
        "{\n"
        '  "selected_article_index": 1,\n'
        '  "top_headline": "",\n'
        '  "summary": "",\n'
        '  "why_it_matters": "",\n'
        '  "keywords": ["", "", ""],\n'
        '  "confidence": 0.0\n'
        "}"
    )


def build_trend_prompt(country_name: str, candidates: list[TrendCandidate]) -> str:
    posts = []
    for index, item in enumerate(candidates, start=1):
        posts.append(
            {
                "index": index,
                "title": item.title,
                "platform": item.platform,
                "source_label": item.source_label,
                "score_label": item.score_label,
                "published_at": item.published_at,
                "source_url": item.source_url,
                "external_url": item.external_url,
                "context": item.context,
            }
        )

    return (
        "You are a cross-cultural meme and trend explainer.\n"
        "Given a set of candidate trending searches or social posts from one country, "
        "choose the single most interesting one for an outsider and explain it.\n"
        "Rules:\n"
        "- Be concise. Explain why people find it funny, controversial, or relatable.\n"
        "- Do not over-explain obvious jokes. Avoid offensive stereotypes.\n"
        "- If political, explain neutrally.\n"
        "- Prefer trends that are specific, culturally revealing, weird, surprising, emotionally legible, or obviously native to local internet culture.\n"
        "- Strongly prefer Reddit posts and YouTube trends (real internet culture) over Google Trends search terms, which are usually just news.\n"
        "- Prefer jokes, memes, formats, fandom moments, and things people share for fun over hard-news headlines.\n"
        "- Avoid generic search terms, routine market moves, basic sports score checks, and shallow celebrity gossip unless the context shows a bigger cultural reason people care.\n"
        "- Avoid yearly reruns, scheduled hype cycles, and stale recurring topics unless there is a clear fresh twist that makes people care this time.\n"
        "- Sports is only worth picking if it is about a major milestone, national icon, or unusually intense local obsession.\n"
        "- If the candidates are weak or generic, still choose the best one but lower confidence.\n"
        "- Be tight: 'plain_english_explanation' under 28 words, 'why_people_are_sharing_it' under 18 words, 'local_context' under 16 words. No filler.\n"
        "- Output valid JSON only.\n"
        f"Country: {country_name}\n"
        f"Candidates: {json.dumps(posts, ensure_ascii=False)}\n"
        "Return:\n"
        "{\n"
        '  "selected_candidate_index": 1,\n'
        '  "meme_title": "",\n'
        '  "plain_english_explanation": "",\n'
        '  "why_people_are_sharing_it": "",\n'
        '  "tone": "funny | angry | ironic | wholesome | chaotic | political | sad | unclear",\n'
        '  "local_context": "",\n'
        '  "keywords": ["", "", ""],\n'
        '  "confidence": 0.0\n'
        "}"
    )


def call_openai_json(prompt: str, model: str, timeout: float) -> dict[str, Any]:
    api_key = load_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set and key.txt was not found.")

    base_url = DEFAULT_BASE_URL.rstrip("/")
    response = requests.post(
        f"{base_url}/chat/completions",
        timeout=timeout,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": "Return valid JSON only. Do not use markdown fences.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        },
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    return parse_json_object(content)


def load_openai_api_key() -> str | None:
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key.strip()

    for path in [Path.cwd() / "key.txt", PROJECT_ROOT / "key.txt"]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        first_line = text.splitlines()[0].strip()
        if first_line.startswith("OPENAI_API_KEY="):
            return first_line.split("=", 1)[1].strip()
        return first_line

    return None


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def clamp_index(raw_value: Any, length: int) -> int:
    try:
        index = int(raw_value)
    except (TypeError, ValueError):
        index = 1
    index = max(1, index)
    return min(index, max(length, 1))


def clean_keywords(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        keyword = item.strip()
        if not keyword:
            continue
        key = normalize_key(keyword)
        if not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(keyword)
        if len(cleaned) == 3:
            break
    return cleaned


def append_keywords(base: list[str], extra: list[str], limit: int = 3) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    for keyword in base + extra:
        if len(merged) >= limit:
            break
        key = normalize_key(keyword)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(keyword)

    return merged


def clean_confidence(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(number, 1.0))


def build_short_explanations_prompt(
    country_name: str,
    kind: str,
    candidates: list[Any],
) -> str:
    payload = []
    for index, item in enumerate(candidates, start=1):
        context = item.context if kind == "trend" else item.snippet
        payload.append({"index": index, "title": item.title, "context": context})

    noun = "trending topics" if kind == "trend" else "news headlines"
    return (
        f"You are labeling {noun} from {country_name} for a global culture map.\n"
        "For EACH item, write ONE very short explanation for an outsider: what it is "
        "and why locals care.\n"
        "Rules:\n"
        "- Hard limit 16 words. One sentence. Plain and concrete, no preamble.\n"
        "- Do not invent facts. If an item is unclear, use \"Unclear local trend.\"\n"
        "- Output valid JSON only.\n"
        f"Items: {json.dumps(payload, ensure_ascii=False)}\n"
        "Return:\n"
        '{ "items": [ {"index": 1, "short": ""} ] }'
    )


def parse_short_explanations(response: dict[str, Any], total: int) -> dict[int, str]:
    parsed: dict[int, str] = {}
    items = response.get("items")
    if not isinstance(items, list):
        return parsed
    for item in items:
        if not isinstance(item, dict):
            continue
        index = clamp_index(item.get("index"), total)
        short = item.get("short")
        if isinstance(short, str) and short.strip():
            parsed[index] = short.strip()
    return parsed


def attach_short_explanations(
    config: CountryConfig,
    kind: str,
    candidates: list[Any],
    args: argparse.Namespace,
) -> None:
    """Batch-explain every shortlisted candidate in a single LLM call so the
    frontend feed can show a short blurb per item, not just the #1 pick.
    Failures are non-fatal — the feed falls back to raw context."""
    if not candidates:
        return
    try:
        response = call_openai_json(
            build_short_explanations_prompt(config.country_name, kind, candidates),
            model=args.model,
            timeout=args.timeout,
        )
        mapping = parse_short_explanations(response, len(candidates))
    except Exception as exc:  # noqa: BLE001
        print(
            f"[probe] short-explanation pass failed for {config.iso2} ({kind}): {exc}",
            file=sys.stderr,
        )
        return

    for index, candidate in enumerate(candidates, start=1):
        text = mapping.get(index)
        if text:
            candidate.short_explanation = text


def build_country_card(
    config: CountryConfig,
    news_candidates: list[NewsCandidate],
    trend_candidates: list[TrendCandidate],
    news_diagnostic: dict[str, Any] | None,
    trend_diagnostics: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    # Batch-explain the full shortlist first so raw_candidates carry a short
    # blurb each (used by the frontend "More signals" feed).
    if not args.dry_run:
        attach_short_explanations(config, "news", news_candidates, args)
        attach_short_explanations(config, "trend", trend_candidates, args)

    card: dict[str, Any] = {
        "iso2": config.iso2,
        "country_name": config.country_name,
        "updated_at": now_utc(),
        "probe_status": "candidate_only" if args.dry_run else "ok",
        "top_news": None,
        "meme": None,
        "keywords": [],
        "raw_candidates": {
            "news": [asdict(item) for item in news_candidates],
            "trends": [asdict(item) for item in trend_candidates],
        },
        "fetch_diagnostics": {
            "news": news_diagnostic,
            "trends": trend_diagnostics,
        },
    }

    if args.dry_run:
        if news_candidates:
            card["top_news"] = {
                "headline": news_candidates[0].title,
                "summary": None,
                "why_it_matters": None,
                "source_name": news_candidates[0].source_name,
                "source_url": news_candidates[0].source_url,
                "published_at": news_candidates[0].published_at,
                "confidence": None,
            }
        if trend_candidates:
            card["meme"] = {
                "title": trend_candidates[0].title,
                "platform": trend_candidates[0].platform,
                "explanation": None,
                "why_people_are_sharing_it": None,
                "tone": None,
                "local_context": None,
                "source_url": trend_candidates[0].source_url,
                "media_url": trend_candidates[0].external_url,
                "confidence": None,
            }
        return card

    errors: list[str] = []

    if news_candidates:
        try:
            news_json = call_openai_json(
                build_news_prompt(config.country_name, news_candidates),
                model=args.model,
                timeout=args.timeout,
            )
            selected_index = clamp_index(
                news_json.get("selected_article_index"),
                len(news_candidates),
            )
            selected = news_candidates[selected_index - 1]
            card["top_news"] = {
                "headline": news_json.get("top_headline") or selected.title,
                "summary": news_json.get("summary"),
                "why_it_matters": news_json.get("why_it_matters"),
                "source_name": selected.source_name,
                "source_url": selected.source_url,
                "published_at": selected.published_at,
                "confidence": clean_confidence(news_json.get("confidence")),
            }
            card["keywords"] = clean_keywords(news_json.get("keywords"))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"news: {exc}")

    if trend_candidates:
        try:
            trend_json = call_openai_json(
                build_trend_prompt(config.country_name, trend_candidates),
                model=args.model,
                timeout=args.timeout,
            )
            selected_index = clamp_index(
                trend_json.get("selected_candidate_index"),
                len(trend_candidates),
            )
            selected = trend_candidates[selected_index - 1]
            card["meme"] = {
                "title": trend_json.get("meme_title") or selected.title,
                "platform": selected.platform,
                "explanation": trend_json.get("plain_english_explanation"),
                "why_people_are_sharing_it": trend_json.get("why_people_are_sharing_it"),
                "tone": trend_json.get("tone"),
                "local_context": trend_json.get("local_context"),
                "source_url": selected.source_url,
                "media_url": selected.external_url,
                "confidence": clean_confidence(trend_json.get("confidence")),
            }
            trend_keywords = clean_keywords(trend_json.get("keywords"))
            card["keywords"] = append_keywords(card["keywords"], trend_keywords, limit=3)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"trend: {exc}")

    if errors:
        card["probe_status"] = "partial"
        card["errors"] = errors

    return card


def write_outputs(cards: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    combined_path = output_dir / "probe-results.json"
    combined_path.write_text(
        json.dumps(cards, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    for card in cards:
        country_path = output_dir / f"{card['iso2']}.json"
        country_path.write_text(
            json.dumps(card, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def selected_configs(args: argparse.Namespace) -> list[CountryConfig]:
    country_codes = args.countries or list(COUNTRIES)
    return [COUNTRIES[code] for code in country_codes]


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    cards: list[dict[str, Any]] = []
    use_ai_assist = (not args.dry_run) and bool(load_openai_api_key())

    for config in selected_configs(args):
        print(f"[probe] collecting {config.iso2} ({config.country_name})", file=sys.stderr)
        try:
            news_candidates, news_diagnostic = fetch_news_candidates(
                config,
                limit=args.news_limit,
                timeout=args.timeout,
            )
        except Exception as exc:  # noqa: BLE001
            news_candidates = []
            news_diagnostic = {
                "source": "google_news_top_rss",
                "status": "error",
                "message": str(exc),
            }
            print(f"[probe] news fetch failed for {config.iso2}: {exc}", file=sys.stderr)

        news_candidates, news_ranking = rank_news_candidates(
            config,
            news_candidates,
            args.news_limit,
        )
        news_diagnostic["filters"] = news_ranking

        trend_candidates, trend_source_diagnostics = fetch_meme_candidates(
            config,
            limit=args.trend_limit,
            timeout=args.timeout,
        )

        trend_candidates, trend_ranking = rank_trend_candidates(
            config,
            trend_candidates,
            args.trend_limit,
            args.model,
            args.timeout,
            use_ai_assist,
        )

        trend_diagnostics = {**trend_source_diagnostics, "filters": trend_ranking}

        card = build_country_card(
            config,
            news_candidates,
            trend_candidates,
            news_diagnostic,
            trend_diagnostics,
            args,
        )
        cards.append(card)

    write_outputs(cards, output_dir)
    print(f"[probe] wrote {len(cards)} cards to {output_dir}", file=sys.stderr)

    if args.stdout:
        print(json.dumps(cards, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
