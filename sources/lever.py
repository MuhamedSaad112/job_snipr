"""JobSnipr source — Lever public company job boards (official ATS, highest quality)."""

from __future__ import annotations

from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "Lever"

COMPANIES = ["netflix", "palantir", "attentive", "ramp", "clari"]


def fetch(http: HttpClient) -> list[dict]:
    jobs: list[dict] = []
    for company in COMPANIES:
        data = http.get_json(f"https://api.lever.co/v0/postings/{company}?mode=json")
        if not isinstance(data, list):
            continue
        for j in data:
            job = empty_job()
            categories = j.get("categories", {}) or {}
            job.update({
                "title": j.get("text", ""),
                "company": company.capitalize(),
                "url": j.get("hostedUrl", ""),
                "location": categories.get("location", ""),
                "category": categories.get("team", ""),
                "description": (j.get("descriptionPlain") or "")[:800],
                "posted_date": str(j.get("createdAt", "")),
                "source": SOURCE_NAME,
            })
            jobs.append(job)
    return jobs
