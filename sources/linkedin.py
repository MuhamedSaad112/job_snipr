"""JobSnipr source — LinkedIn public guest job search (no login)."""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "LinkedIn"

GULF_COUNTRIES = ["UAE", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman", "Egypt"]

TITLE_RE = re.compile(r'class="base-search-card__title"[^>]*>\s*(.*?)\s*</h3>', re.DOTALL)
COMPANY_RE = re.compile(r'class="base-search-card__subtitle"[^>]*>\s*<[^>]+>\s*(.*?)\s*</a>', re.DOTALL)
URL_RE = re.compile(r'class="base-card__full-link[^"]*"\s+href="([^"?]+)')
LOCATION_RE = re.compile(r'class="job-search-card__location"[^>]*>\s*(.*?)\s*</span>', re.DOTALL)


def fetch(http: HttpClient) -> list[dict]:
    jobs: list[dict] = []
    for country in GULF_COUNTRIES:
        url = (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords=java+spring+boot+backend&location={quote_plus(country)}&start=0"
        )
        text = http.get_text(url)
        if not text:
            continue
        titles = TITLE_RE.findall(text)
        companies = COMPANY_RE.findall(text)
        urls = URL_RE.findall(text)
        locations = LOCATION_RE.findall(text)
        for i, job_url in enumerate(urls):
            job = empty_job()
            job.update({
                "title": (titles[i].strip() if i < len(titles) else "Java/Backend Role"),
                "company": (companies[i].strip() if i < len(companies) else ""),
                "url": job_url,
                "location": (locations[i].strip() if i < len(locations) else country),
                "country": country,
                "source": f"{SOURCE_NAME} ({country})",
            })
            jobs.append(job)
    return jobs
