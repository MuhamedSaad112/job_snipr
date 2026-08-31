"""JobSnipr source — Indeed regional RSS feeds."""

from __future__ import annotations

from sources.base import empty_job
from utils.http_client import HttpClient

SOURCE_NAME = "Indeed"

FEEDS = [
    ("https://ae.indeed.com/rss?q=java+spring+boot+backend&l=", "UAE"),
    ("https://sa.indeed.com/rss?q=java+spring+boot+backend&l=", "Saudi Arabia"),
    ("https://qa.indeed.com/rss?q=java+spring+boot+backend&l=", "Qatar"),
    ("https://kw.indeed.com/rss?q=java+spring+boot+backend&l=", "Kuwait"),
    ("https://bh.indeed.com/rss?q=java+spring+boot+backend&l=", "Bahrain"),
    ("https://www.indeed.com/rss?q=java+spring+boot&l=Dubai", "Dubai"),
    ("https://www.indeed.com/rss?q=java+spring+boot&l=Riyadh", "Riyadh"),
]


def fetch(http: HttpClient) -> list[dict]:
    jobs: list[dict] = []
    for feed_url, country in FEEDS:
        root = http.get_xml(feed_url)
        if root is None:
            continue
        for item in root.iter("item"):
            title = item.findtext("title", "") or ""
            company = ""
            if " - " in title:
                title, company = title.rsplit(" - ", 1)
                title, company = title.strip(), company.strip()
            job = empty_job()
            job.update({
                "title": title,
                "company": company,
                "url": item.findtext("link", "") or "",
                "location": country,
                "country": country,
                "description": (item.findtext("description", "") or "")[:500],
                "posted_date": item.findtext("pubDate", "") or "",
                "source": f"{SOURCE_NAME} ({country})",
            })
            jobs.append(job)
    return jobs
