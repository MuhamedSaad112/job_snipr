"""JobSnipr source — Arbeitnow (public JSON API)."""

from __future__ import annotations

from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "Arbeitnow"


def fetch(http: HttpClient) -> list[dict]:
    data = http.get_json("https://www.arbeitnow.com/api/job-board-api")
    if not data:
        return []
    jobs = []
    for j in data.get("data", [])[:60]:
        job = empty_job()
        job.update({
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "url": j.get("url", ""),
            "location": j.get("location", "") or "Remote",
            "tags": ", ".join(j.get("tags", []) or []),
            "description": (j.get("description") or "")[:800],
            "posted_date": str(j.get("created_at", "")),
            "source": SOURCE_NAME,
        })
        jobs.append(job)
    return jobs
