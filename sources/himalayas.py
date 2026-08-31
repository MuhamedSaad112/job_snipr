"""JobSnipr source — Himalayas (public JSON API)."""

from __future__ import annotations

from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "Himalayas"


def fetch(http: HttpClient) -> list[dict]:
    data = http.get_json("https://himalayas.app/jobs/api?skills=java&skills=spring-boot&limit=40")
    if not data:
        return []
    jobs = []
    for j in data.get("jobs", []):
        job = empty_job()
        job.update({
            "title": j.get("title", ""),
            "company": (j.get("company") or {}).get("name", ""),
            "url": j.get("applicationLink", ""),
            "location": j.get("location", "") or "Remote",
            "tags": ", ".join(s.get("name", "") for s in (j.get("skills") or [])),
            "description": (j.get("excerpt") or "")[:800],
            "posted_date": str(j.get("pubDate", "") or ""),
            "source": SOURCE_NAME,
        })
        jobs.append(job)
    return jobs
