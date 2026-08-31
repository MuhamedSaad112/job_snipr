"""
JobSnipr — Source Base
Every source module exposes a single function:

    def fetch(http: HttpClient) -> list[dict]

...returning normalized dicts matching this shape:

    {
        "title": "", "company": "", "url": "", "location": "",
        "country": "", "tags": "", "salary": "", "category": "",
        "description": "", "source": "", "posted_date": "",
    }

A source must never raise past its own fetch() — main.py wraps every
call so one broken source can't stop the polling loop, but sources
should still catch what they reasonably can and log via the shared
logger.
"""

from __future__ import annotations

import json
import re

NORMALIZED_KEYS = (
    "title", "company", "url", "location", "country", "tags",
    "salary", "category", "description", "source", "posted_date",
)


def empty_job() -> dict:
    return {k: "" for k in NORMALIZED_KEYS}


_JSONLD_RE = re.compile(
    r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL
)


def extract_jsonld_jobs(html: str, page_url: str, source_name: str) -> list[dict]:
    """Parse schema.org JobPosting JSON-LD blocks out of a page — used
    by several board-scraping sources (Bayt, Naukrigulf, GulfTalent,
    Wuzzuf) that publish structured data but no public API."""
    jobs: list[dict] = []
    for match in _JSONLD_RE.findall(html or ""):
        try:
            data = json.loads(match)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict) or item.get("@type") != "JobPosting":
                continue
            loc_data = item.get("jobLocation", {})
            if isinstance(loc_data, list):
                loc_data = loc_data[0] if loc_data else {}
            addr = loc_data.get("address", {}) if isinstance(loc_data, dict) else {}
            locality = addr.get("addressLocality", "") if isinstance(addr, dict) else ""
            country = addr.get("addressCountry", "") if isinstance(addr, dict) else ""
            job = empty_job()
            job.update({
                "title": item.get("title", ""),
                "company": (item.get("hiringOrganization") or {}).get("name", "")
                if isinstance(item.get("hiringOrganization"), dict) else "",
                "url": item.get("url", page_url),
                "location": f"{locality} {country}".strip(),
                "country": country,
                "description": (item.get("description") or "")[:500],
                "posted_date": item.get("datePosted", ""),
                "source": source_name,
            })
            jobs.append(job)
    return jobs
