"""
JobSnipr — Source Registry
Central list of every job source. Adding a new source means writing a
`fetch(http) -> list[dict]` function in its own module and registering
it here — nothing else in the app needs to change.
"""

from __future__ import annotations

from sources import (
    adzuna,
    arbeitnow,
    bayt,
    greenhouse,
    gulftalent,
    himalayas,
    indeed,
    jobicy,
    jsearch,
    lever,
    linkedin,
    naukrigulf,
    remoteok,
    remotive,
    weworkremotely,
    wuzzuf,
)

# (display_name, fetch_fn)
SOURCE_REGISTRY: list[tuple[str, callable]] = [
    ("Bayt.com", bayt.fetch),
    ("Naukrigulf", naukrigulf.fetch),
    ("GulfTalent", gulftalent.fetch),
    ("Wuzzuf", wuzzuf.fetch),
    ("LinkedIn Gulf", linkedin.fetch),
    ("Indeed Gulf", indeed.fetch),
    ("Adzuna Gulf", adzuna.fetch),
    ("JSearch", jsearch.fetch),
    ("Greenhouse", greenhouse.fetch),
    ("Lever", lever.fetch),
    ("Remotive", remotive.fetch),
    ("RemoteOK", remoteok.fetch),
    ("Arbeitnow", arbeitnow.fetch),
    ("Jobicy", jobicy.fetch),
    ("Himalayas", himalayas.fetch),
    ("WeWorkRemotely", weworkremotely.fetch),
]
