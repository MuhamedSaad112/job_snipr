"""JobSnipr source — Jobicy (public JSON API)."""

from __future__ import annotations

from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "Jobicy"


def fetch(http: HttpClient) -> list[dict]:
    data = http.get_json("https://jobicy.com/api/v2/remote-jobs?count=40&tag=java")
    if not data:
        return []
    jobs = []
    for j in data.get("jobs", []):
        job = empty_job()
        job.update({
            "title": j.get("jobTitle", ""),
            "company": j.get("companyName", ""),
            "url": j.get("url", ""),
            "location": j.get("jobGeo", "") or "Remote",
            "tags": ", ".join(j.get("jobIndustry", []) or []),
            "salary": str(j.get("annualSalaryMin", "") or ""),
            "description": (j.get("jobExcerpt") or "")[:800],
            "posted_date": j.get("pubDate", ""),
            "source": SOURCE_NAME,
        })
        jobs.append(job)
    return jobs
