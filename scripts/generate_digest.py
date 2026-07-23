#!/usr/bin/env python3
"""Write Morning Çay — the Brief's daily digest — to site/data/digest.json.

With ANTHROPIC_API_KEY set, a Claude model writes the digest from the day's
top stories. Without it (or on any API failure) an automated headline roundup
is produced instead, so the card is never empty and the workflow never fails.

The digest is regenerated once per Istanbul day; set FORCE_DIGEST=1 to rewrite.
Env: ANTHROPIC_API_KEY, DIGEST_MODEL (default claude-sonnet-5), FORCE_DIGEST.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ISTANBUL = ZoneInfo("Europe/Istanbul")
DATA_DIR = Path(
    os.environ.get("BRIEF_DATA_DIR")
    or Path(__file__).resolve().parents[1] / "site" / "data"
)
API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5"

CATEGORY_NAMES = {
    "turkiye": "Türkiye",
    "region": "Around the region",
    "migration": "Migration & residency",
    "rights": "Rights & freedoms",
    "safety": "Safety",
    "economy": "Money",
}

EDITOR_PROMPT = """\
You are the editor of The Bosphorus Brief, a short daily briefing for
international residents of Türkiye and the wider region — teachers, students,
NGO and development professionals, entrepreneurs, researchers, and families
living there long-term.

Voice and standards (strict):
- Calm, practical, plainspoken. Never sensational; never speculate beyond the
  sources given.
- Neutral on politics and religion. Do not attach religious, ethnic, or
  political labels to individuals or communities, and avoid activist framing.
- Always ask: what does this mean for a resident's daily life — residency
  paperwork, money, safety, travel, schooling? Lead with that.
- The material tags outlets with an ownership lens (state media,
  pro-government, opposition-leaning, independent, international). When the
  framing of a major story clearly diverges between lenses, note it in one
  calm sentence ("State-aligned outlets emphasize X; international coverage
  focuses on Y"). If an important story appears in only one lens, you may
  say so plainly. Describe outlets, never speculate about motives.
- Standing priorities, whenever the material includes them: court rulings
  and administrative actions touching foreign residents' legal security —
  deportations, entry bans, visa and residency refusals, cases before the
  European Court of Human Rights — and freedom-of-belief or other
  civil-liberty developments affecting any community in the region. Give
  these space even on busy news days, reported plainly and without drama.
- If safety news is included, be steady and specific, not alarming.
- 250-400 words total. Write in English; Turkish terms (ikamet, çay) are fine
  where natural.

Return ONLY a JSON object, no markdown fences, with exactly these keys:
{
  "title": "a short, warm title for today's digest",
  "overview": "2-3 sentence read on the day",
  "sections": [{"heading": "...", "body": "one tight paragraph"}, ...],
  "closing": "one short, human sign-off sentence"
}
Use 3-5 sections drawn from what actually matters today, not one per category
by obligation."""


def log(msg: str) -> None:
    print(f"[digest] {msg}", flush=True)


LENS_WORDS = {
    "state": "state media",
    "progov": "pro-government",
    "opposition": "opposition-leaning",
    "independent": "independent",
    "international": "international",
    "official": "official",
}


def tagged_source(item: dict) -> str:
    lens = LENS_WORDS.get(item.get("lens"))
    return f"[{item['source']}{' · ' + lens if lens else ''}]"


def coverage_note(item: dict) -> str:
    others = [
        f"{c['source']} ({LENS_WORDS.get(c.get('lens'), 'unlabeled')})"
        for c in item.get("coverage", [])
        if c["source"] != item["source"]
    ][:5]
    return f" | also covered by: {', '.join(others)}" if others else ""


def build_material(news: dict, rates: dict | None, quakes: dict | None = None) -> str:
    by_id = {i["id"]: i for i in news.get("items", [])}
    lines = ["TOP STORIES:"]
    for item_id in news.get("top", [])[:10]:
        item = by_id.get(item_id)
        if item:
            lines.append(
                f"- {tagged_source(item)} {item['title']} "
                f"({item.get('published') or 'n/a'})"
                + (f" — {item['summary']}" if item.get("summary") else "")
                + coverage_note(item)
            )
    for cat, label in CATEGORY_NAMES.items():
        picks = [i for i in news.get("items", []) if i["category"] == cat][:5]
        if picks:
            lines.append(f"\n{label.upper()}:")
            lines.extend(
                f"- {tagged_source(i)} {i['title']}{coverage_note(i)}"
                for i in picks
            )
    advisories = news.get("advisories", [])
    if advisories:
        lines.append("\nUS TRAVEL ADVISORY LEVELS: " + ", ".join(
            f"{a['country']} L{a['level']}" for a in advisories))
    if rates and rates.get("pairs"):
        lines.append("EXCHANGE RATES: " + ", ".join(
            f"{p['pair']} {p['rate']}" for p in rates["pairs"]))
    if quakes and quakes.get("quakes"):
        lines.append("RECENT EARTHQUAKES M4+ IN/NEAR TÜRKIYE (USGS): " + "; ".join(
            f"M{q['mag']} {q['place']} ({q['time'][:10]})"
            for q in quakes["quakes"][:5]))
    return "\n".join(lines)


def ai_digest(material: str, today_label: str, api_key: str) -> dict:
    model = os.environ.get("DIGEST_MODEL", "").strip() or DEFAULT_MODEL
    resp = requests.post(
        API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 3000,
            "system": EDITOR_PROMPT,
            "messages": [{
                "role": "user",
                "content": f"Today is {today_label}. Write today's digest "
                           f"from this material:\n\n{material}",
            }],
        },
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"API {resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    if body.get("stop_reason") == "max_tokens":
        raise ValueError("model response truncated at max_tokens")
    text = "".join(
        block.get("text", "") for block in body.get("content", [])
    ).strip()
    if "{" in text:  # tolerate markdown fences or stray prose around the JSON
        text = text[text.index("{"):text.rindex("}") + 1]
    digest = json.loads(text)
    for key in ("title", "overview", "sections"):
        if key not in digest:
            raise ValueError(f"model response missing '{key}'")
    digest["method"] = "ai"
    digest["model"] = model
    return digest


def headline_digest(news: dict) -> dict:
    by_id = {i["id"]: i for i in news.get("items", [])}
    sections = []
    for cat, label in CATEGORY_NAMES.items():
        picks = [
            by_id[i] for i in news.get("top", []) if by_id.get(i, {}).get("category") == cat
        ] or [i for i in news.get("items", []) if i["category"] == cat]
        if picks:
            sections.append({
                "heading": label,
                "body": " · ".join(
                    f"{i['title']} ({i['source']})" for i in picks[:3]
                ),
            })
    return {
        "title": "This morning's headlines",
        "overview": "An automated roundup of the most recent stories across "
                    "the Brief's sources. Add an ANTHROPIC_API_KEY secret and "
                    "tomorrow's çay comes with a written briefing.",
        "sections": sections,
        "closing": "Full stories in the feed below.",
        "method": "headlines",
    }


def main() -> int:
    news_path = DATA_DIR / "news.json"
    digest_path = DATA_DIR / "digest.json"
    if not news_path.exists():
        log("no news.json — nothing to digest")
        return 0
    news = json.loads(news_path.read_text())
    rates = None
    rates_path = DATA_DIR / "rates.json"
    if rates_path.exists():
        try:
            rates = json.loads(rates_path.read_text())
        except json.JSONDecodeError:
            rates = None
    quakes = None
    quakes_path = DATA_DIR / "quakes.json"
    if quakes_path.exists():
        try:
            quakes = json.loads(quakes_path.read_text())
        except json.JSONDecodeError:
            quakes = None

    now_ist = datetime.now(ISTANBUL)
    today = now_ist.date().isoformat()
    force = os.environ.get("FORCE_DIGEST", "") not in ("", "0", "false")
    if digest_path.exists() and not force:
        try:
            existing = json.loads(digest_path.read_text())
            if existing.get("date") == today and existing.get("method") == "ai":
                log(f"digest for {today} already written — keeping it")
                return 0
        except json.JSONDecodeError:
            pass

    today_label = now_ist.strftime("%A, %d %B %Y")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    digest = None
    if api_key:
        try:
            digest = ai_digest(
                build_material(news, rates, quakes), today_label, api_key)
            log(f"AI digest written ({digest['model']})")
        except Exception as exc:  # noqa: BLE001 — fall back rather than fail
            log(f"AI digest failed ({exc}) — falling back to headlines")
    if digest is None:
        digest = headline_digest(news)
        log("headline digest written")

    digest["date"] = today
    digest["date_label"] = today_label
    digest["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    digest_path.write_text(json.dumps(digest, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
