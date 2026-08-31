"""JobSnipr source — Remotive (public JSON API)."""

from __future__ import annotations

from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "Remotive"


def fetch(http: HttpClient) -> list[dict]:
    data = http.get_json("https://remotive.com/api/remote-jobs?search=java&limit=60")
    if not data:
        return []
    jobs = []
    for j in data.get("jobs", []):
        job = empty_job()
        job.update({
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "url": j.get("url", ""),
            "location": j.get("candidate_required_location", "Remote"),
            "tags": ", ".join(j.get("tags", []) or []),
            "salary": j.get("salary", "") or "",
            "category": j.get("category", "") or "",
            "description": (j.get("description") or "")[:800],
            "source": SOURCE_NAME,
            "posted_date": j.get("publication_date", ""),
        })
        jobs.append(job)
    return jobs
