#!/usr/bin/env python3
"""Export Phase 0 probe output into Phase 1 static frontend data files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

COUNTRY_META: dict[str, dict[str, Any]] = {
    "US": {"iso3": "USA", "region": "North America", "coordinates": {"lat": 39.8283, "lon": -98.5795}},
    "CA": {"iso3": "CAN", "region": "North America", "coordinates": {"lat": 56.1304, "lon": -106.3468}},
    "GB": {"iso3": "GBR", "region": "Europe", "coordinates": {"lat": 54.0, "lon": -2.5}},
    "FR": {"iso3": "FRA", "region": "Europe", "coordinates": {"lat": 46.6034, "lon": 1.8883}},
    "DE": {"iso3": "DEU", "region": "Europe", "coordinates": {"lat": 51.1657, "lon": 10.4515}},
    "JP": {"iso3": "JPN", "region": "East Asia", "coordinates": {"lat": 36.2048, "lon": 138.2529}},
    "KR": {"iso3": "KOR", "region": "East Asia", "coordinates": {"lat": 36.5, "lon": 127.8}},
    "CN": {"iso3": "CHN", "region": "East Asia", "coordinates": {"lat": 35.8617, "lon": 104.1954}},
    "IN": {"iso3": "IND", "region": "South Asia", "coordinates": {"lat": 22.5937, "lon": 78.9629}},
    "BR": {"iso3": "BRA", "region": "South America", "coordinates": {"lat": -14.2350, "lon": -51.9253}},
    "MX": {"iso3": "MEX", "region": "North America", "coordinates": {"lat": 23.6345, "lon": -102.5528}},
    "AR": {"iso3": "ARG", "region": "South America", "coordinates": {"lat": -38.4161, "lon": -63.6167}},
    "AU": {"iso3": "AUS", "region": "Oceania", "coordinates": {"lat": -25.2744, "lon": 133.7751}},
    "RU": {"iso3": "RUS", "region": "Europe / Asia", "coordinates": {"lat": 61.5240, "lon": 105.3188}},
    "UA": {"iso3": "UKR", "region": "Europe", "coordinates": {"lat": 48.3794, "lon": 31.1656}},
    "TR": {"iso3": "TUR", "region": "Europe / Asia", "coordinates": {"lat": 38.9637, "lon": 35.2433}},
    "ID": {"iso3": "IDN", "region": "Southeast Asia", "coordinates": {"lat": -2.5, "lon": 118.0}},
    "PH": {"iso3": "PHL", "region": "Southeast Asia", "coordinates": {"lat": 12.8797, "lon": 121.7740}},
    "ZA": {"iso3": "ZAF", "region": "Africa", "coordinates": {"lat": -30.5595, "lon": 22.9375}},
    "NG": {"iso3": "NGA", "region": "Africa", "coordinates": {"lat": 9.0820, "lon": 8.6753}},
}


def iso2_to_flag(iso2: str) -> str:
    if not iso2 or len(iso2) != 2 or not iso2.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(char) - ord("A")) for char in iso2.upper())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export probe results into public/data for the Phase 1 prototype."
    )
    parser.add_argument(
        "--input",
        default="outputs/phase0/probe-results.json",
        help="Probe results JSON produced by scripts/probe.py.",
    )
    parser.add_argument(
        "--output-dir",
        default="public/data",
        help="Directory where normalized frontend data will be written.",
    )
    return parser.parse_args()


def load_cards(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Expected probe results to be a list of country cards.")
    return payload


def clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def clean_keywords(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def clean_top_news(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    headline = clean_text(value.get("headline"))
    if not headline:
        return None
    return {
        "headline": headline,
        "summary": clean_text(value.get("summary")),
        "why_it_matters": clean_text(value.get("why_it_matters")),
        "source_name": clean_text(value.get("source_name")),
        "source_url": clean_text(value.get("source_url")),
        "published_at": clean_text(value.get("published_at")),
        "confidence": value.get("confidence"),
    }


def clean_meme(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    title = clean_text(value.get("title"))
    if not title:
        return None
    return {
        "title": title,
        "platform": clean_text(value.get("platform")),
        "explanation": clean_text(value.get("explanation")),
        "why_people_are_sharing_it": clean_text(value.get("why_people_are_sharing_it")),
        "tone": clean_text(value.get("tone")),
        "local_context": clean_text(value.get("local_context")),
        "source_url": clean_text(value.get("source_url")),
        "media_url": clean_text(value.get("media_url")),
        "confidence": value.get("confidence"),
    }


def build_overview(card: dict[str, Any]) -> dict[str, Any]:
    meta = COUNTRY_META.get(card["iso2"], {})
    top_news = clean_top_news(card.get("top_news"))
    meme = clean_meme(card.get("meme"))
    return {
        "iso2": card["iso2"],
        "iso3": meta.get("iso3"),
        "country_name": clean_text(card.get("country_name")) or card["iso2"],
        "flag": iso2_to_flag(card["iso2"]),
        "region": meta.get("region"),
        "coordinates": meta.get("coordinates"),
        "updated_at": clean_text(card.get("updated_at")),
        "probe_status": clean_text(card.get("probe_status")),
        "keywords": clean_keywords(card.get("keywords")),
        "news_headline": top_news["headline"] if top_news else None,
        "news_confidence": top_news.get("confidence") if top_news else None,
        "meme_title": meme["title"] if meme else None,
        "meme_tone": meme.get("tone") if meme else None,
        "meme_confidence": meme.get("confidence") if meme else None,
        "has_top_news": bool(top_news),
        "has_meme": bool(meme),
    }


def build_full_card(card: dict[str, Any]) -> dict[str, Any]:
    meta = COUNTRY_META.get(card["iso2"], {})
    return {
        "iso2": card["iso2"],
        "iso3": meta.get("iso3"),
        "country_name": clean_text(card.get("country_name")) or card["iso2"],
        "flag": iso2_to_flag(card["iso2"]),
        "region": meta.get("region"),
        "coordinates": meta.get("coordinates"),
        "updated_at": clean_text(card.get("updated_at")),
        "probe_status": clean_text(card.get("probe_status")),
        "keywords": clean_keywords(card.get("keywords")),
        "top_news": clean_top_news(card.get("top_news")),
        "meme": clean_meme(card.get("meme")),
        "fetch_diagnostics": card.get("fetch_diagnostics") or {},
        "raw_candidates": card.get("raw_candidates") or {},
    }


def build_layer_records(cards: list[dict[str, Any]], layer: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for card in cards:
        item = card.get(layer)
        if not item:
            continue
        if layer == "top_news":
            records.append(
                {
                    "iso2": card["iso2"],
                    "country_name": card["country_name"],
                    "headline": item["headline"],
                    "summary": item.get("summary"),
                    "confidence": item.get("confidence"),
                    "source_url": item.get("source_url"),
                }
            )
        else:
            records.append(
                {
                    "iso2": card["iso2"],
                    "country_name": card["country_name"],
                    "title": item["title"],
                    "tone": item.get("tone"),
                    "explanation": item.get("explanation"),
                    "confidence": item.get("confidence"),
                    "source_url": item.get("source_url"),
                    "media_url": item.get("media_url"),
                }
            )
    return records


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    input_path = PROJECT_ROOT / args.input
    output_dir = PROJECT_ROOT / args.output_dir
    cards = load_cards(input_path)

    normalized_cards = [build_full_card(card) for card in cards]
    overviews = [build_overview(card) for card in normalized_cards]

    write_json(
        output_dir / "countries.json",
        {
            "generated_from": str(input_path.relative_to(PROJECT_ROOT)),
            "updated_at": max(
                (card.get("updated_at") for card in normalized_cards if card.get("updated_at")),
                default=None,
            ),
            "countries": overviews,
        },
    )

    for card in normalized_cards:
        write_json(output_dir / "countries" / f"{card['iso2']}.json", card)

    write_json(
        output_dir / "layers" / "news.json",
        {
            "updated_at": max(
                (card.get("updated_at") for card in normalized_cards if card.get("updated_at")),
                default=None,
            ),
            "countries": build_layer_records(normalized_cards, "top_news"),
        },
    )
    write_json(
        output_dir / "layers" / "memes.json",
        {
            "updated_at": max(
                (card.get("updated_at") for card in normalized_cards if card.get("updated_at")),
                default=None,
            ),
            "countries": build_layer_records(normalized_cards, "meme"),
        },
    )

    print(f"[export] wrote frontend data to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
