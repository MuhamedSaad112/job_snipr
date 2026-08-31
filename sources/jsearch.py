"""JobSnipr source — JSearch via RapidAPI (aggregates Indeed/LinkedIn/Glassdoor)."""

from __future__ import annotations

from config import settings
from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "JSearch"

QUERIES = [
    "java spring boot developer in UAE",
    "java backend developer in Saudi Arabia",
    "software engineer java in Qatar",
    "java developer in Kuwait OR Bahrain OR Oman",
]


def fetch(http: HttpClient) -> list[dict]:
    if not settings.jsearch_key:
        return []
    jobs: list[dict] = []
    for q in QUERIES:
        data = http.get_json(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key": settings.jsearch_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            params={"query": q, "page": "1", "num_pages": "1", "date_posted": "week"},
        )
        if not data:
            continue
        for j in data.get("data", []):
            salary = ""
            if j.get("job_min_salary"):
                salary = f"{j.get('job_salary_currency', '')} {j.get('job_min_salary', '')}".strip()
            job = empty_job()
            job.update({
                "title": j.get("job_title", ""),
                "company": j.get("employer_name", ""),
                "url": j.get("job_apply_link", ""),
                "location": f"{j.get('job_city', '')} {j.get('job_country', '')}".strip(),
                "country": j.get("job_country", ""),
                "salary": salary,
                "description": (j.get("job_description") or "")[:800],
                "posted_date": j.get("job_posted_at_datetime_utc", ""),
                "source": SOURCE_NAME,
            })
            jobs.append(job)
    return jobs
