"""
JobSnipr — Domain Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RawJob:
    """A job exactly as normalized from a source, before scoring."""

    title: str = ""
    company: str = ""
    url: str = ""
    location: str = ""
    country: str = ""
    tags: str = ""
    salary: str = ""
    category: str = ""
    description: str = ""
    source: str = ""
    posted_date: str = ""
    source_quality: int = 5


@dataclass
class DomainScore:
    score: int
    accepted: bool
    matched_categories: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


@dataclass
class CVMatchResult:
    score: int
    level: str
    emoji: str
    matched_skills: list[str] = field(default_factory=list)
    partial_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level,
            "matched_skills": self.matched_skills,
            "partial_skills": self.partial_skills,
            "missing_skills": self.missing_skills,
            "reasons": self.reasons,
        }


@dataclass
class ProcessedJob:
    """A job that has passed normalization, dedup and domain relevance,
    and is ready for scoring, persistence and delivery."""

    raw: RawJob
    fingerprint: str
    domain: DomainScore
    cv_match: CVMatchResult
    priority: str
    seniority: str = "Unknown"
    job_type: str = "Unknown"
    tracks: list[str] = field(default_factory=list)
    discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
