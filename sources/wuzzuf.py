"""JobSnipr source — Wuzzuf (Egypt & Gulf, JSON-LD scraping)."""

from __future__ import annotations

from sources.base import extract_jsonld_jobs
from utils.http_client import HttpClient

SOURCE_NAME = "Wuzzuf"


def fetch(http: HttpClient) -> list[dict]:
    url = "https://wuzzuf.net/search/jobs/?q=java+spring+backend&a=hpb"
    text = http.get_text(url)
    if not text:
        return []
    return extract_jsonld_jobs(text, url, SOURCE_NAME)
