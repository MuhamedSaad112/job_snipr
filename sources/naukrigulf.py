"""JobSnipr source — Naukrigulf (JSON-LD scraping)."""

from __future__ import annotations

from sources.base import extract_jsonld_jobs
from utils.http_client import HttpClient

SOURCE_NAME = "Naukrigulf"

QUERIES = ["java-developer", "spring-boot-developer", "backend-developer"]


def fetch(http: HttpClient) -> list[dict]:
    jobs: list[dict] = []
    for q in QUERIES:
        url = f"https://www.naukrigulf.com/{q}-jobs"
        text = http.get_text(url)
        if text:
            jobs.extend(extract_jsonld_jobs(text, url, SOURCE_NAME))
    return jobs
