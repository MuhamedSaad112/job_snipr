"""
JobSnipr — Normalization
Turns raw per-source dicts into a canonical RawJob, validates required
fields, escapes HTML for safe Telegram delivery, and computes freshness
and priority metadata.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

from models import RawJob

REQUIRED_FIELDS = ("title", "company", "url")


def normalize_job(raw: dict) -> RawJob | None:
    """Build a RawJob from a source dict. Returns None if required
    fields are missing (a broken/partial source record is dropped,
    not crashed on)."""
    title = (raw.get("title") or "").strip()
    company = (raw.get("company") or "").strip()
    url = (raw.get("url") or "").strip()

    if not title or not url:
        return None
    if not company:
        company = "Not specified"

    return RawJob(
        title=title,
        company=company,
        url=url,
        location=(raw.get("location") or "").strip(),
        country=(raw.get("country") or "").strip(),
        tags=(raw.get("tags") or "").strip(),
        salary=(raw.get("salary") or "").strip(),
        category=(raw.get("category") or "").strip(),
        description=(raw.get("description") or "").strip(),
        source=(raw.get("source") or "Unknown").strip(),
        posted_date=(raw.get("posted_date") or "").strip(),
        source_quality=int(raw.get("source_quality", 5)),
    )


def escape_html(text: str) -> str:
    """Escape a field for Telegram HTML parse_mode. Job titles and
    company names frequently contain & < > which would otherwise
    break message rendering."""
    if not text:
        return ""
    return html.escape(text, quote=False)


def compute_freshness(posted_date: str) -> str:
    """Return one of: 'Very Fresh', 'Fresh', 'Recent', 'Older', 'Unknown'."""
    if not posted_date:
        return "Unknown"
    try:
        dt = dateutil_parser.parse(posted_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except (ValueError, OverflowError, TypeError):
        return "Unknown"

    if age_hours < 24:
        return "Very Fresh"
    if age_hours < 72:
        return "Fresh"
    if age_hours < 168:
        return "Recent"
    return "Older"


def compute_priority(cv_score: int, domain_score: int, source_quality: int, is_target_location: bool, freshness: str) -> str:
    """HIGH / MEDIUM / NORMAL priority — used internally for ordering
    and optionally surfaced in the personal Telegram message."""
    points = 0
    points += cv_score * 0.5
    points += domain_score * 0.2
    points += source_quality * 2
    points += 10 if is_target_location else 0
    points += {"Very Fresh": 10, "Fresh": 6, "Recent": 2, "Older": 0, "Unknown": 0}.get(freshness, 0)

    if points >= 70 and cv_score >= 75:
        return "🔥 HIGH PRIORITY"
    if points >= 45:
        return "⭐ MEDIUM PRIORITY"
    return "📌 NORMAL"
