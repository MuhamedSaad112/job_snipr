"""JobSnipr source — Adzuna Gulf (free API, requires ADZUNA_APP_ID/KEY)."""

from __future__ import annotations

from config import settings
from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "Adzuna"

COUNTRY_CODES = ["ae", "sa", "qa", "kw"]


def fetch(http: HttpClient) -> list[dict]:
    if not settings.adzuna_app_id:
        return []
    jobs: list[dict] = []
    for code in COUNTRY_CODES:
        data = http.get_json(
            f"https://api.adzuna.com/v1/api/jobs/{code}/search/1",
            params={
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_api_key,
                "results_per_page": 30,
                "what": "java spring boot backend",
                "content-type": "application/json",
            },
        )
        if not data:
            continue
        for j in data.get("results", []):
            sal_min = j.get("salary_min", "")
            sal_max = j.get("salary_max", "")
            salary = f"{sal_min}-{sal_max}".strip("-") if (sal_min or sal_max) else ""
            job = empty_job()
            job.update({
                "title": j.get("title", ""),
                "company": (j.get("company") or {}).get("display_name", ""),
                "url": j.get("redirect_url", ""),
                "location": (j.get("location") or {}).get("display_name", ""),
                "salary": salary,
                "description": (j.get("description") or "")[:800],
                "posted_date": j.get("created", ""),
                "source": f"{SOURCE_NAME} ({code.upper()})",
            })
            jobs.append(job)
    return jobs
