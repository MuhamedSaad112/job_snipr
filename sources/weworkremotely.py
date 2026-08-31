"""JobSnipr source — WeWorkRemotely (RSS)."""

from __future__ import annotations

from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "WeWorkRemotely"


def fetch(http: HttpClient) -> list[dict]:
    root = http.get_xml("https://weworkremotely.com/categories/remote-programming-jobs.rss")
    if root is None:
        return []
    jobs = []
    for item in root.iter("item"):
        title = item.findtext("title", "") or ""
        company = ""
        if ": " in title:
            company, title = title.split(": ", 1)
        job = empty_job()
        job.update({
            "title": title.strip(),
            "company": company.strip(),
            "url": item.findtext("link", "") or "",
            "location": "Remote",
            "description": (item.findtext("description", "") or "")[:800],
            "posted_date": item.findtext("pubDate", "") or "",
            "source": SOURCE_NAME,
        })
        jobs.append(job)
    return jobs
