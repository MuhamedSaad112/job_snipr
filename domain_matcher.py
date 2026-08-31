"""
JobSnipr — Domain Relevance Engine
Scores a job 0-100 against the Java/Backend/Integration ecosystem using
weighted, capped category contributions (never a flat `if keyword in text`
scan), then applies acceptance RULES A-D plus an exclusion engine so
generic DevOps/Data-Engineering/Frontend roles are rejected unless real
Java/backend/integration evidence overrides the exclusion.
"""

from __future__ import annotations

from models import DomainScore
from taxonomy import (
    CATEGORIES,
    CONTEXT_REQUIRED_KEYWORDS,
    EXCLUSION_TITLE_PHRASES,
    INTEGRATION_TITLE_PHRASES,
    STRONG_TITLE_PHRASES,
    contains_phrase,
    count_hits,
    normalize_text,
)

# Tracks for job classification (doc's JOB_CLASSIFICATION section)
TRACK_CATEGORY_MAP = {
    "core_java": "JAVA_BACKEND",
    "spring": "SPRING_BOOT",
    "microservices": "MICROSERVICES",
    "messaging": "KAFKA" ,  # refined below per-keyword
    "integration": "INTEGRATION",
    "api_web": "API_ENGINEERING",
    "database": "DATABASE_BACKEND",
    "java_fullstack": "JAVA_FULL_STACK",
    "cloud_devops": "CLOUD_NATIVE_BACKEND",
}


def _category_points(haystack: str, category_key: str) -> tuple[int, list[str]]:
    """Score one category: each distinct keyword hit contributes a
    diminishing share of the category's max weight, capped at the max
    (so repeating 'Java' ten times never inflates the score)."""
    cat = CATEGORIES[category_key]
    weight = cat["weight"]
    hits = count_hits(haystack, cat["keywords"])
    if not hits:
        return 0, []
    # First hit worth 55% of weight, remaining hits share the rest,
    # capped — rewards breadth without unbounded stacking.
    base = weight * 0.55
    remainder = weight * 0.45
    extra = min(len(hits) - 1, 6)  # cap extra contributing hits
    points = base + (remainder * extra / 6 if extra else 0)
    return round(min(points, weight)), hits


def compute_domain_score(title: str, description: str, tags: str, category: str) -> DomainScore:
    haystack = normalize_text(" ".join([title, description, tags, category]))
    title_norm = normalize_text(title)

    total = 0
    matched_categories: list[str] = []
    reasons: list[str] = []
    category_hits: dict[str, list[str]] = {}

    for cat_key in CATEGORIES:
        pts, hits = _category_points(haystack, cat_key)
        if pts > 0:
            total += pts
            matched_categories.append(cat_key)
            category_hits[cat_key] = hits

    total = min(total, 100)

    has_strong_title = any(contains_phrase(title_norm, p) for p in STRONG_TITLE_PHRASES)
    has_integration_title = any(contains_phrase(title_norm, p) for p in INTEGRATION_TITLE_PHRASES)

    if has_strong_title:
        reasons.append("Title directly matches a core Java/Backend/Integration role")

    # ---- Exclusion engine ----
    is_excluded_title = any(contains_phrase(title_norm, p) for p in EXCLUSION_TITLE_PHRASES)
    strong_categories_present = sum(
        1 for k in ("spring", "microservices", "messaging", "integration")
        if k in matched_categories
    )

    if is_excluded_title and not has_strong_title:
        # Positive evidence can override: needs real Java/Spring/backend
        # signal, not just an incidentally-mentioned cloud keyword.
        override = (
            "core_java" in matched_categories or "spring" in matched_categories
        ) and strong_categories_present >= 1
        if not override:
            return DomainScore(
                score=min(total, 20),
                accepted=False,
                matched_categories=matched_categories,
                reasons=["Excluded title with no Java/Spring/backend override"],
            )
        reasons.append("Excluded-sounding title overridden by strong Java/Spring evidence")

    # ---- Context-required keyword guard ----
    # If the ONLY matched categories are ones built entirely from
    # context-required keywords (Kafka/Kubernetes/Docker/cloud alone),
    # and there's no core_java/spring/backend_context/integration hit,
    # reject regardless of raw score.
    core_context_present = any(
        k in matched_categories
        for k in ("core_java", "spring", "backend_context", "integration")
    )
    if not core_context_present:
        return DomainScore(
            score=min(total, 30),
            accepted=False,
            matched_categories=matched_categories,
            reasons=["Only tangential technologies matched — no core Java/backend/integration context"],
        )

    # ---- Acceptance rules ----
    accepted = False

    # RULE A: relevant title + score >= threshold-ish baseline
    if has_strong_title and total >= 35:
        accepted = True
        reasons.append("RULE A: relevant title + sufficient domain score")

    # RULE B: integration/backend title + 2+ strong techs
    if not accepted and has_integration_title:
        strong_tech_cats = sum(
            1 for k in ("spring", "messaging", "microservices", "integration")
            if k in matched_categories
        )
        if strong_tech_cats >= 2:
            accepted = True
            reasons.append("RULE B: integration/backend title + 2+ strong technologies")

    # RULE C: Java Full Stack title + Java/Spring context
    if not accepted and "java_fullstack" in matched_categories:
        if "core_java" in matched_categories or "spring" in matched_categories:
            accepted = True
            reasons.append("RULE C: Java Full Stack title + Java/Spring Boot context")

    # RULE D: Enterprise Integration role + Java-adjacent integration tech
    if not accepted and has_integration_title and "integration" in matched_categories:
        accepted = True
        reasons.append("RULE D: enterprise integration role with relevant integration technology")

    # Fallback: no strong title, but broad+deep technical evidence
    if not accepted and total >= 55 and strong_categories_present >= 2:
        accepted = True
        reasons.append("Strong combined technical evidence across multiple core categories")

    if not accepted:
        reasons.append("Did not satisfy any acceptance rule (A/B/C/D) or fallback threshold")

    return DomainScore(
        score=total, accepted=accepted, matched_categories=matched_categories, reasons=reasons
    )


def classify_tracks(domain: DomainScore, title: str, description: str) -> list[str]:
    """Map matched categories + specific keywords to display tracks."""
    haystack = normalize_text(" ".join([title, description]))
    tracks: list[str] = []

    if "core_java" in domain.matched_categories:
        tracks.append("JAVA_BACKEND")
    if "spring" in domain.matched_categories:
        tracks.append("SPRING_BOOT")
    if "microservices" in domain.matched_categories:
        tracks.append("MICROSERVICES")
    if "messaging" in domain.matched_categories:
        if contains_phrase(haystack, "kafka"):
            tracks.append("KAFKA")
        tracks.append("MESSAGING")
        if contains_phrase(haystack, "event driven"):
            tracks.append("EVENT_DRIVEN")
    if "integration" in domain.matched_categories:
        tracks.append("INTEGRATION")
    if "api_web" in domain.matched_categories:
        tracks.append("API_ENGINEERING")
    if "database" in domain.matched_categories:
        tracks.append("DATABASE_BACKEND")
    if "java_fullstack" in domain.matched_categories:
        tracks.append("JAVA_FULL_STACK")
    if "cloud_devops" in domain.matched_categories:
        tracks.append("CLOUD_NATIVE_BACKEND")
    if "microservices" in domain.matched_categories and "core_java" in domain.matched_categories:
        tracks.append("DISTRIBUTED_SYSTEMS")
    if any(k in domain.matched_categories for k in ("core_java", "spring", "backend_context")):
        tracks.append("ENTERPRISE_SOFTWARE")

    # de-dupe, preserve order
    seen = set()
    ordered = []
    for t in tracks:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered
