"""JobSnipr source — GulfTalent (JSON-LD scraping)."""

from __future__ import annotations

from urllib.parse import quote_plus

from sources.base import extract_jsonld_jobs
from utils.http_client import HttpClient

SOURCE_NAME = "GulfTalent"

QUERIES = ["java developer", "spring boot", "backend developer", "integration engineer"]


def fetch(http: HttpClient) -> list[dict]:
    jobs: list[dict] = []
    for q in QUERIES:
        url = f"https://www.gulftalent.com/jobs/search?q={quote_plus(q)}"
        text = http.get_text(url)
        if text:
            jobs.extend(extract_jsonld_jobs(text, url, SOURCE_NAME))
    return jobs
