"""Unit tests for the pure (network-free) parts of the probe pipeline:
text helpers, the rule-based filter, hard-drop behavior, and the source quota.
"""

import probe
from probe import (
    COUNTRIES,
    TREND_SOURCE_QUOTAS,
    NewsCandidate,
    TrendCandidate,
    apply_source_quota,
    clamp_index,
    clean_confidence,
    clean_keywords,
    is_valid_wikipedia_article,
    looks_like_bare_person_name,
    normalize_key,
    parse_short_explanations,
    parse_traffic_score,
    parse_trend_ai_hints,
    rank_trend_candidates,
    strip_html,
)

US = COUNTRIES["US"]


def trend(title, platform="google_trends", context="some story", rank=500):
    return TrendCandidate(
        title=title,
        platform=platform,
        source_label="x",
        score_label="x",
        rank_score=rank,
        published_at="",
        source_url=f"https://example.com/{normalize_key(title)}",
        external_url=f"https://example.com/{normalize_key(title)}",
        context=context,
    )


# ---- text / cleaning helpers ------------------------------------------------

def test_normalize_key_strips_and_lowercases():
    assert normalize_key("Hello, World!") == "helloworld"
    assert normalize_key("") == ""


def test_parse_traffic_score():
    assert parse_traffic_score("50,000+") == 50000
    assert parse_traffic_score("traffic unavailable") == 0


def test_clamp_index_stays_in_range():
    assert clamp_index(5, 3) == 3
    assert clamp_index(0, 3) == 1
    assert clamp_index("not a number", 3) == 1
    assert clamp_index(2, 3) == 2


def test_clean_confidence_clamps():
    assert clean_confidence(0.5) == 0.5
    assert clean_confidence(5) == 1.0
    assert clean_confidence(-1) == 0.0
    assert clean_confidence("abc") is None


def test_clean_keywords_dedupes_and_caps_at_three():
    assert clean_keywords(["a", "a", "b", "c", "d"]) == ["a", "b", "c"]
    assert clean_keywords(["ok", 5, "", "  "]) == ["ok"]
    assert clean_keywords("not a list") == []


def test_strip_html():
    assert strip_html("<b>Hi</b>  &amp; bye") == "Hi & bye"


def test_is_valid_wikipedia_article():
    assert is_valid_wikipedia_article("Shohei_Ohtani") is True
    assert is_valid_wikipedia_article("Main_Page") is False
    assert is_valid_wikipedia_article("2026") is False
    assert is_valid_wikipedia_article("July_4") is False
    assert is_valid_wikipedia_article("Special:Search") is False


# ---- bare-person-name detection --------------------------------------------

def test_bare_person_name_detection():
    # bare names -> True
    assert looks_like_bare_person_name("村上宗隆") is True
    assert looks_like_bare_person_name("Bernie Sanders") is True
    # CJK with an event marker is not a bare name
    assert looks_like_bare_person_name("米騒動") is False
    # generic query words are blocklisted, not treated as a name
    assert looks_like_bare_person_name("stock market today") is False


# ---- filter pipeline: hard drops must not leak ------------------------------

def test_hard_dropped_trends_never_reach_shortlist():
    candidates = [
        trend("nba scores"),
        trend("weather"),
        trend("horoscope"),
        trend("stock market today"),
        trend("Whale crashes fireboat", context="a whale hit a fireboat"),
    ]
    shortlist, diagnostics = rank_trend_candidates(
        US, candidates, limit=8, model="x", timeout=1, use_ai_assist=False
    )
    titles = [c.title for c in shortlist]
    assert titles == ["Whale crashes fireboat"]
    # the generic queries are recorded as dropped, not kept
    dropped = [d for d in diagnostics if not d["passed"]]
    assert dropped and all(d["kept"] is False for d in dropped)


# ---- source quota -----------------------------------------------------------

def test_source_quota_guarantees_minimum_reddit():
    passing = [trend(f"yt{i}", platform="youtube", rank=1000 - i) for i in range(6)]
    passing += [trend(f"rd{i}", platform="reddit", rank=500 - i) for i in range(4)]

    out = apply_source_quota(passing, limit=8, quotas=TREND_SOURCE_QUOTAS)
    platforms = [c.platform for c in out]

    assert len(out) == 8
    assert platforms.count("reddit") >= 3   # quota guaranteed
    assert platforms.count("youtube") >= 3
    # higher-ranked youtube still leads (order preserves rank)
    assert platforms[0] == "youtube"


def test_source_quota_handles_scarce_source():
    passing = [trend(f"yt{i}", platform="youtube", rank=1000 - i) for i in range(8)]
    passing += [trend("rd0", platform="reddit", rank=10)]
    out = apply_source_quota(passing, limit=8, quotas=TREND_SOURCE_QUOTAS)
    assert len(out) == 8
    # only one reddit exists, so it is included but not fabricated
    assert [c.platform for c in out].count("reddit") == 1


# ---- LLM-response parsers ---------------------------------------------------

def test_parse_short_explanations_skips_blanks():
    resp = {"items": [{"index": 1, "short": "hi"}, {"index": 2, "short": "  "}]}
    assert parse_short_explanations(resp, 2) == {1: "hi"}
    assert parse_short_explanations({}, 2) == {}


def test_parse_trend_ai_hints_clamps_adjustment():
    resp = {"hints": [{"index": 1, "score_adjustment": 9, "normalized_title": "X", "reason": "r"}]}
    parsed = parse_trend_ai_hints(resp, total_candidates=3)
    assert parsed[1]["score_adjustment"] == 3
    assert parsed[1]["normalized_title"] == "X"
