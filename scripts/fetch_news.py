#!/usr/bin/env python3
"""Aggregate the Brief's sources into site/data/*.json.

Design goals:
- Never produce a worse site than the one already deployed: on total failure
  the existing JSON files are left untouched and the run still exits 0.
- Any individual feed may fail (timeouts, format drift, outages) without
  affecting the others.

Usage: fetch_news.py [--out-dir DIR] [--skip-rates] [--max-age-days N]
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

sys.path.insert(0, str(Path(__file__).parent))
from feeds import (  # noqa: E402
    ADVISORY_COUNTRIES, ADVISORY_FEED, ADVISORY_LABELS, BOOST_WORDS,
    FEEDS, QUAKES_URL, RATES_URL, blocked_source, source_lens,
)

UA = "BosphorusBrief/1.0 (+static news briefing; contact via repository)"
TIMEOUT = 20
TOP_COUNT = 14
MAX_PER_SOURCE_IN_TOP = 2

# Headline translation for Turkish/Arabic feeds. Results are cached in
# site/data/translations.json (committed back by the workflow) so each
# headline is translated exactly once.
API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_TRANSLATE_MODEL = "claude-haiku-4-5-20251001"
TRANSLATE_BATCH = 40
CACHE_KEEP_DAYS = 21
LANG_NAMES = {"tr": "Turkish", "ar": "Arabic"}

TRANSLATE_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["id", "title"],
            },
        },
    },
    "required": ["items"],
}

TRANSLATE_PROMPT = (
    "You translate news headlines and summaries into natural English for a "
    "daily briefing. Keep proper names, institutions, and Turkish terms that "
    "residents use (ikamet, tahdit kodu) with a short gloss if needed. Stay "
    "strictly faithful to the original — never add, soften, or editorialize. "
    "Write headlines in plain headline style. If a summary is empty, return "
    "an empty summary. Submit every item via the publish_translations tool."
)

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
# Google News appends " - Publisher" to titles.
GN_SUFFIX_RE = re.compile(r"\s+-\s+[^-]{2,60}$")
# Arabic/Hebrew, CJK, Hangul, Kana — the Brief is an English-language feed.
NON_LATIN_RE = re.compile(r"[֐-ࣿ一-鿿가-힯぀-ヿ]")
# "Turkey" the bird and "Turkey" the American place name are the price of
# keyword feeds. Stories about poultry, holidays, hunting, and small-town
# US life are never Brief material.
JUNK_TITLE_RE = re.compile(
    r"\b(?:poultry|thanksgiving|butterball|obituar\w*|funeral home"
    r"|turkey (?:trot|hunt\w*|season|call\w*|vulture|breast|burger|bacon"
    r"|sandwich|dinner|recipe\w*|drive|bowl|leg|farm\w*|prices? per pound"
    r"|giveaway|shoot|decoy)"
    r"|wild turkey|roast(?:ed)? turkey|fried turkey|smoked turkey"
    r"|turkey (?:creek|foot|valley|point|run) (?:rd|road|high school|school"
    r"|nuclear|park)"
    r"|concession stand|varsity)\b",
    re.IGNORECASE,
)
# A title datelined "Somewhere, KY" is a US local story, not regional news.
US_LOCALITY_RE = re.compile(
    r",\s(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|IA|ID|IL|IN|KS|KY|LA|MA|MD|ME"
    r"|MI|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX"
    r"|UT|VA|VT|WA|WI|WV|WY)\b"
)


def log(msg: str) -> None:
    print(f"[fetch] {msg}", flush=True)


def clean_text(raw: str, limit: int = 300) -> str:
    text = WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text


def entry_time(entry) -> str | None:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime.fromtimestamp(
                    time.mktime(parsed), tz=timezone.utc
                ).isoformat(timespec="seconds")
            except (OverflowError, ValueError):
                continue
    return None


def fetch_feed(feed: dict) -> list[dict]:
    resp = requests.get(feed["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    items = []
    for entry in parsed.entries[: feed["max"]]:
        link = getattr(entry, "link", "") or ""
        title = clean_text(getattr(entry, "title", ""), 220)
        if not link or not title:
            continue
        source = feed["source"]
        if feed["source"] == "Google News":
            src = getattr(entry, "source", None)
            source = clean_text(getattr(src, "title", "") or "", 60) or "Google News"
            title = GN_SUFFIX_RE.sub("", title)
        if blocked_source(source):
            continue
        # The stray-language filter guards keyword feeds; feeds that declare
        # a language are foreign on purpose and get translated instead.
        if not feed.get("lang") and \
                len(NON_LATIN_RE.findall(f"{title} {source}")) >= 3:
            continue
        if JUNK_TITLE_RE.search(title) or US_LOCALITY_RE.search(title):
            continue
        summary = clean_text(
            getattr(entry, "summary", "") or getattr(entry, "description", "")
        )
        # Google News often echoes "title + publisher" as the description —
        # noise, not a summary.
        title_key = re.sub(r"[^a-z0-9]+", "", title.lower())
        summary_key = re.sub(r"[^a-z0-9]+", "", summary.lower())
        if summary_key.startswith(title_key) and \
                len(summary_key) - len(title_key) <= 40:
            summary = ""
        required = feed.get("require")
        if required:
            text = f"{title} {summary}".lower()
            if not any(term in text for term in required):
                continue
        item = {
            "id": hashlib.sha1(link.encode()).hexdigest()[:12],
            "title": title,
            "url": link,
            "source": source,
            "category": feed["category"],
            "published": entry_time(entry),
            "summary": summary,
            "weight": feed["weight"],
        }
        if feed.get("lang"):
            item["lang"] = feed["lang"]
        items.append(item)
    return items


def translate_items(items: list[dict], out_dir: Path, now: datetime) -> None:
    """Translate foreign-language items to English, caching by item id."""
    foreign = [i for i in items if i.get("lang") and i["lang"] != "en"]
    if not foreign:
        return
    cache_path = out_dir / "translations.json"
    try:
        cache = json.loads(cache_path.read_text())
    except (OSError, json.JSONDecodeError):
        cache = {}

    def apply(item: dict, entry: dict) -> None:
        item["orig_title"] = item["title"]
        item["title"] = entry["title"]
        item["summary"] = entry.get("summary") or ""
        item["translated"] = True

    pending = []
    for item in foreign:
        hit = cache.get(item["id"])
        if hit:
            apply(item, hit)
        else:
            pending.append(item)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    translated_now = 0
    if pending and api_key:
        batch = pending[:TRANSLATE_BATCH]
        model = os.environ.get("TRANSLATE_MODEL", "").strip() \
            or DEFAULT_TRANSLATE_MODEL
        material = json.dumps(
            [{"id": i["id"], "lang": LANG_NAMES.get(i["lang"], i["lang"]),
              "title": i["title"], "summary": i["summary"]} for i in batch],
            ensure_ascii=False,
        )
        resp = requests.post(
            API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 8000,
                "system": TRANSLATE_PROMPT,
                "tools": [{
                    "name": "publish_translations",
                    "description": "Publish the English translations.",
                    "input_schema": TRANSLATE_SCHEMA,
                }],
                "tool_choice": {"type": "tool", "name": "publish_translations"},
                "messages": [{
                    "role": "user",
                    "content": "Translate these items to English:\n" + material,
                }],
            },
            timeout=120,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"API {resp.status_code}: {resp.text[:300]}")
        body = resp.json()
        result = next(
            (b.get("input") for b in body.get("content", [])
             if b.get("type") == "tool_use"
             and b.get("name") == "publish_translations"),
            None,
        )
        if not isinstance(result, dict):
            raise ValueError("no publish_translations call in model response")
        by_id = {i["id"]: i for i in batch}
        stamp = now.isoformat(timespec="seconds")
        for t in result.get("items", []):
            item = by_id.get(t.get("id"))
            if not item or not t.get("title"):
                continue
            entry = {"title": t["title"].strip(),
                     "summary": (t.get("summary") or "").strip(),
                     "ts": stamp}
            cache[item["id"]] = entry
            apply(item, entry)
            translated_now += 1

    # Keep the cache small: current items plus a short trailing window.
    keep_after = (now - timedelta(days=CACHE_KEEP_DAYS)).isoformat()
    current = {i["id"] for i in foreign}
    cache = {k: v for k, v in cache.items()
             if k in current or v.get("ts", "") >= keep_after}
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    log(f"translated: {translated_now} new, "
        f"{len(foreign) - len(pending)} cached, "
        f"{max(0, len(pending) - translated_now)} left original")


CLUSTER_STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "to", "and", "as", "at", "by",
    "with", "after", "amid", "over", "from", "into", "says", "say", "said",
    "new", "his", "her", "its", "their", "this", "that", "will", "has", "have",
    "was", "are", "turkey", "turkiye", "turkish",
}


def title_tokens(title: str) -> set[str]:
    words = re.findall(r"[a-z0-9çğıöşü]+", title.lower())
    return {w for w in words if len(w) > 2 and w not in CLUSTER_STOPWORDS}


def cluster(items: list[dict]) -> list[dict]:
    """Group the same event reported by different outlets into one story.

    Returns one item per cluster (the strongest member becomes the face of
    the story) with `coverage` listing every outlet that reported it, a
    `lens` for the primary source, and a `blindspot` marker when an event
    with multiple reports appears in only one ownership lens.
    """
    ordered = sorted(
        items, key=lambda i: (i["weight"], i["published"] or ""), reverse=True
    )
    clusters: list[dict] = []
    seen_urls: set[str] = set()
    for item in ordered:
        url_key = item["url"].split("?")[0].rstrip("/").lower()
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)
        tokens = title_tokens(item["title"])
        target = None
        for c in clusters:
            base = min(len(tokens), len(c["tokens"]))
            if base >= 4 and len(tokens & c["tokens"]) / base >= 0.6:
                target = c
                break
        if target is None:
            clusters.append({"tokens": tokens, "members": [item]})
        else:
            target["members"].append(item)

    out = []
    for c in clusters:
        by_source: dict[str, dict] = {}
        for member in c["members"]:  # first hit per outlet wins (syndication)
            by_source.setdefault(member["source"], member)
        members = list(by_source.values())
        item = dict(members[0])
        lens = source_lens(item["source"])
        if lens:
            item["lens"] = lens["code"]
            item["lens_note"] = lens["note"]
        if len(members) > 1:
            coverage = []
            for member in sorted(
                members, key=lambda m: m["published"] or "", reverse=True
            ):
                member_lens = source_lens(member["source"])
                coverage.append({
                    "source": member["source"],
                    "url": member["url"],
                    "published": member["published"],
                    "lens": member_lens["code"] if member_lens else None,
                })
            item["coverage"] = coverage
            lenses = {m["lens"] for m in coverage} - {None, "official"}
            if lenses and lenses <= {"state", "progov"}:
                item["blindspot"] = "progov"
            elif lenses == {"opposition"}:
                item["blindspot"] = "opposition"
        out.append(item)
    return out


def score(item: dict, now: datetime) -> float:
    pts = float(item["weight"])
    if item["published"]:
        age_h = (now - datetime.fromisoformat(item["published"])).total_seconds() / 3600
        pts += max(0.0, 48 - age_h) / 12  # up to +4 for freshness
    text = f"{item['title']} {item['summary']}".lower()
    pts += sum(0.5 for word in BOOST_WORDS if word in text)
    pts += 0.6 * min(len(item.get("coverage", [])), 6)  # widely covered = bigger
    return pts


def pick_top(items: list[dict], now: datetime) -> list[str]:
    ranked = sorted(items, key=lambda i: score(i, now), reverse=True)
    top: list[str] = []
    per_source: dict[str, int] = {}
    for item in ranked:
        if per_source.get(item["source"], 0) >= MAX_PER_SOURCE_IN_TOP:
            continue
        top.append(item["id"])
        per_source[item["source"]] = per_source.get(item["source"], 0) + 1
        if len(top) >= TOP_COUNT:
            break
    return top


ADVISORY_TITLE_RE = re.compile(
    r"^(?P<country>.+?)\s*[-–—]\s*Level\s*(?P<level>[1-4])", re.IGNORECASE
)


def fetch_advisories() -> list[dict]:
    resp = requests.get(ADVISORY_FEED, headers={"User-Agent": UA}, timeout=TIMEOUT)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    wanted = {c.lower(): c for c in ADVISORY_COUNTRIES}
    found: dict[str, dict] = {}
    for entry in parsed.entries:
        match = ADVISORY_TITLE_RE.match(getattr(entry, "title", "") or "")
        if not match:
            continue
        country = match.group("country").strip()
        if country.lower() not in wanted:
            continue
        label = ADVISORY_LABELS.get(country, country)
        found[label] = {
            "country": label,
            "level": int(match.group("level")),
            "title": clean_text(entry.title, 160),
            "url": getattr(entry, "link", "") or "",
            "updated": entry_time(entry),
        }
    order = []
    for name in ADVISORY_COUNTRIES:
        label = ADVISORY_LABELS.get(name, name)
        if label in found and found[label] not in order:
            order.append(found[label])
    return order


def fetch_rates() -> dict | None:
    resp = requests.get(RATES_URL, headers={"User-Agent": UA}, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    rates = data.get("rates", {})
    try_rate = rates.get("TRY")
    if not try_rate:
        return None
    pairs = [{"pair": "USD/TRY", "rate": round(try_rate, 2)}]
    for ccy in ("EUR", "GBP"):
        if rates.get(ccy):
            pairs.append({"pair": f"{ccy}/TRY", "rate": round(try_rate / rates[ccy], 2)})
    return {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "open.er-api.com (mid-market, updated daily)",
        "pairs": pairs,
    }


def fetch_quakes() -> dict | None:
    resp = requests.get(QUAKES_URL, headers={"User-Agent": UA}, timeout=TIMEOUT)
    resp.raise_for_status()
    quakes = []
    for feature in resp.json().get("features", []):
        props = feature.get("properties", {})
        if props.get("mag") is None or not props.get("time"):
            continue
        quakes.append({
            "mag": round(float(props["mag"]), 1),
            "place": clean_text(props.get("place") or "", 90) or "—",
            "time": datetime.fromtimestamp(
                props["time"] / 1000, tz=timezone.utc
            ).isoformat(timespec="seconds"),
            "url": props.get("url") or "",
        })
    if not quakes:
        return None
    return {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "USGS",
        "quakes": quakes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parents[1] / "site" / "data"),
    )
    parser.add_argument("--skip-rates", action="store_true")
    parser.add_argument("--max-age-days", type=int, default=10)
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.max_age_days)

    items: list[dict] = []
    ok, failed = [], []
    for feed in FEEDS:
        try:
            fetched = fetch_feed(feed)
            fresh = [
                i for i in fetched
                if not i["published"] or datetime.fromisoformat(i["published"]) >= cutoff
            ]
            items.extend(fresh)
            ok.append(feed["id"])
            log(f"{feed['id']}: {len(fresh)} items")
        except Exception as exc:  # noqa: BLE001 — one bad feed must not sink the run
            failed.append(feed["id"])
            log(f"{feed['id']}: FAILED ({exc})")

    try:
        translate_items(items, out_dir, now)
    except Exception as exc:  # noqa: BLE001 — foreign items stay readable as-is
        log(f"translation: FAILED ({exc}) — foreign items shown untranslated")

    # Satire clusters only against itself: a parody must never merge with —
    # or lend coverage weight to — the story it is parodying.
    news_items = [i for i in items if i["category"] != "satire"]
    satire_items = [i for i in items if i["category"] == "satire"]
    items = cluster(news_items) + cluster(satire_items)
    items.sort(key=lambda i: i["published"] or "", reverse=True)

    news_path = out_dir / "news.json"
    if not items:
        log("no items fetched at all — keeping existing news.json")
    else:
        advisories = []
        try:
            advisories = fetch_advisories()
            log(f"advisories: {len(advisories)} countries")
        except Exception as exc:  # noqa: BLE001
            log(f"advisories: FAILED ({exc}) — reusing previous if present")
            if news_path.exists():
                try:
                    advisories = json.loads(news_path.read_text()).get("advisories", [])
                except (json.JSONDecodeError, OSError):
                    advisories = []
        top_ids = pick_top(
            [i for i in items if i["category"] != "satire"], now)
        for item in items:
            item.pop("weight", None)
        payload = {
            "generated_at": now.isoformat(timespec="seconds"),
            "items": items,
            "top": top_ids,
            "advisories": advisories,
            "stats": {"sources_ok": ok, "sources_failed": failed},
        }
        news_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
        log(f"wrote {news_path} ({len(items)} items)")

    if not args.skip_rates:
        try:
            rates = fetch_rates()
            if rates:
                (out_dir / "rates.json").write_text(
                    json.dumps(rates, ensure_ascii=False, indent=1)
                )
                log("wrote rates.json")
        except Exception as exc:  # noqa: BLE001
            log(f"rates: FAILED ({exc}) — keeping existing rates.json")

    try:
        quakes = fetch_quakes()
        if quakes:
            (out_dir / "quakes.json").write_text(
                json.dumps(quakes, ensure_ascii=False, indent=1)
            )
            log(f"quakes: {len(quakes['quakes'])} events")
    except Exception as exc:  # noqa: BLE001
        log(f"quakes: FAILED ({exc}) — keeping existing quakes.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
