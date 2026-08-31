"""
JobSnipr — Smart Deduplication
The same job frequently appears on multiple boards with different URLs.
Instead of URL-only dedup, build a stable fingerprint from normalized
title + company + location so duplicates across LinkedIn / Bayt /
Indeed / company career pages collapse into one entry, and keep the
highest quality source's URL.
"""

from __future__ import annotations

import hashlib
import re

from models import RawJob

SENIORITY_WORDS = {
    "senior", "junior", "sr", "jr", "lead", "principal", "staff", "i", "ii", "iii",
}

_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")

# Source quality scoring, used to prefer the best duplicate.
SOURCE_QUALITY: dict[str, int] = {
    "greenhouse": 10, "lever": 10, "ashby": 10, "workable": 10,
    "smartrecruiters": 10,
    "linkedin": 9,
    "bayt.com": 8, "naukrigulf": 8, "gulftalent": 8,
    "indeed": 7, "adzuna": 7, "jsearch": 7,
    "remotive": 6, "remoteok": 6, "arbeitnow": 6, "jobicy": 6,
    "himalayas": 6, "weworkremotely": 6, "wuzzuf": 6,
}


def source_quality_for(source_name: str) -> int:
    key = source_name.lower()
    for prefix, score in SOURCE_QUALITY.items():
        if prefix in key:
            return score
    return 5


def _clean_words(text: str, strip_seniority: bool = False) -> str:
    t = text.lower()
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    if strip_seniority:
        t = " ".join(w for w in t.split() if w not in SENIORITY_WORDS)
    return t


def compute_fingerprint(title: str, company: str, location: str) -> str:
    """Stable hash across sources for the same underlying job posting."""
    norm_title = _clean_words(title, strip_seniority=True)
    norm_company = _clean_words(company)
    norm_location = _clean_words(location)
    key = f"{norm_title}|{norm_company}|{norm_location}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def better_source(existing_source: str, new_source: str) -> bool:
    """True if new_source should replace existing_source as the
    canonical URL for a duplicate fingerprint."""
    return source_quality_for(new_source) > source_quality_for(existing_source)


def annotate_source_quality(job: RawJob) -> RawJob:
    job.source_quality = source_quality_for(job.source)
    return job
