"""JobSnipr source — RemoteOK (public JSON API)."""

from __future__ import annotations

from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "RemoteOK"


def fetch(http: HttpClient) -> list[dict]:
    data = http.get_json("https://remoteok.com/api")
    if not isinstance(data, list):
        return []
    jobs = []
    for j in data[1:80]:
        if not isinstance(j, dict) or not j.get("position"):
            continue
        job = empty_job()
        url = j.get("url", "")
        job.update({
            "title": j.get("position", ""),
            "company": j.get("company", ""),
            "url": ("https://remoteok.com" + url) if url.startswith("/") else url,
            "location": j.get("location", "Remote") or "Remote",
            "tags": ", ".join(j.get("tags", []) or []),
            "salary": j.get("salary", "") or "",
            "description": (j.get("description") or "")[:800],
            "source": SOURCE_NAME,
            "posted_date": j.get("date", ""),
        })
        jobs.append(job)
    return jobs
