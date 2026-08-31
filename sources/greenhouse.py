"""JobSnipr source — Greenhouse public company job boards (official ATS, highest quality)."""

from __future__ import annotations

from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "Greenhouse"

# Companies known to run Java/backend-heavy engineering orgs with public boards.
COMPANIES = [
    "stripe", "coinbase", "figma", "notion", "brex", "plaid",
    "gusto", "rippling", "intercom", "confluent", "databricks",
]


def fetch(http: HttpClient) -> list[dict]:
    jobs: list[dict] = []
    for company in COMPANIES:
        data = http.get_json(f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs")
        if not data:
            continue
        for j in data.get("jobs", []):
            job = empty_job()
            job.update({
                "title": j.get("title", ""),
                "company": company.capitalize(),
                "url": j.get("absolute_url", ""),
                "location": (j.get("location") or {}).get("name", ""),
                "posted_date": j.get("updated_at", ""),
                "source": SOURCE_NAME,
            })
            jobs.append(job)
    return jobs
