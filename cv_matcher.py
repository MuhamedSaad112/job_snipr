"""
JobSnipr — CV Matching Engine
Transparent, weighted, explainable scoring against Mohamed's actual
CV profile. Never a random percentage — every point traces back to a
specific weighted category and a specific keyword hit.
"""

from __future__ import annotations

from models import CVMatchResult
from taxonomy import STRONG_TITLE_PHRASES, contains_phrase, count_hits, normalize_text

# ══════════════════════════════════════════════════════════════════
#  CV SKILL TIERS  (canonical, lowercase, normalized-text keywords)
# ══════════════════════════════════════════════════════════════════

TIER1_SKILLS = [
    "java", "spring boot", "rest api", "microservices", "kafka",
    "activemq", "postgresql", "jpa", "hibernate", "spring security",
    "jwt", "oauth2", "rbac", "redis", "docker", "ci/cd", "git",
]

TIER2_SKILLS = [
    "spring data jpa", "spring mvc", "event driven architecture",
    "distributed systems", "outbox pattern", "multi-tenancy",
    "liquibase", "elk stack", "websocket", "graphql", "keycloak",
]

TIER3_SKILLS = [
    "kubernetes", "rabbitmq", "aws", "azure", "angular", "react",
    "mongodb", "elasticsearch", "opentelemetry",
]

# Notable named technologies a Java-backend job posting commonly asks
# for. Anything found here that isn't already covered by CV tiers is
# reported as a genuine missing/preferred skill — generic soft skills
# ("team player", "communication") are intentionally excluded.
NOTABLE_JOB_SKILLS = list(dict.fromkeys(
    TIER1_SKILLS + TIER2_SKILLS + TIER3_SKILLS + [
        "mysql", "sql server", "oracle database", "mongodb", "cassandra",
        "dynamodb", "terraform", "jenkins", "github actions", "gitlab ci",
        "graalvm", "spring cloud", "spring batch", "spring integration",
        "apache camel", "mulesoft", "grpc", "protobuf", "avro",
        "node.js", "typescript", "python", "spark", "airflow",
        "prometheus", "grafana", "jenkins", "helm", "openshift",
    ]
))

# ══════════════════════════════════════════════════════════════════
#  SCORE WEIGHTS
# ══════════════════════════════════════════════════════════════════

WEIGHTS = {
    "title": 30,
    "core_skills": 30,
    "architecture": 15,
    "messaging": 10,
    "database": 5,
    "security": 5,
    "devops": 5,
}

ARCHITECTURE_KEYWORDS = [
    "microservices", "distributed systems", "multi-tenancy",
    "domain driven design", "ddd", "event driven architecture",
    "event driven", "cqrs", "saga pattern",
]
MESSAGING_KEYWORDS = ["kafka", "activemq", "rabbitmq", "jms", "outbox pattern", "dead letter queue", "dlq"]
DATABASE_KEYWORDS = ["postgresql", "mysql", "redis", "jpa", "hibernate", "liquibase", "sql"]
SECURITY_KEYWORDS = ["jwt", "oauth2", "rbac", "keycloak", "spring security", "authentication", "authorization"]
DEVOPS_KEYWORDS = ["docker", "ci/cd", "gitlab ci", "github actions", "elk stack"]

MATCH_LEVELS = [
    (90, "Excellent Match", "🔥"),
    (75, "Strong Match", "🟢"),
    (60, "Good Match", "🟡"),
    (40, "Partial Match", "🟠"),
    (0, "Low Match", "⚪"),
]


def _match_level(score: int) -> tuple[str, str]:
    for threshold, label, emoji in MATCH_LEVELS:
        if score >= threshold:
            return label, emoji
    return "Low Match", "⚪"


def _weighted(haystack: str, keywords: list[str], weight: int) -> tuple[int, list[str]]:
    hits = count_hits(haystack, keywords)
    if not hits or not keywords:
        return 0, hits
    fraction = min(1.0, len(hits) / max(1, min(len(keywords), 5)))
    return round(weight * fraction), hits


def compute_cv_match(title: str, description: str, tags: str) -> CVMatchResult:
    haystack = normalize_text(" ".join([title, description, tags]))
    title_norm = normalize_text(title)

    reasons: list[str] = []

    # --- 1. Title match (30 pts) ---
    if any(contains_phrase(title_norm, p) for p in STRONG_TITLE_PHRASES):
        title_pts = WEIGHTS["title"]
        reasons.append("Job title directly aligns with Java Backend Engineer profile")
    elif contains_phrase(title_norm, "java") and any(
        w in title_norm for w in ("backend", "developer", "engineer", "spring")
    ):
        title_pts = round(WEIGHTS["title"] * 0.7)
        reasons.append("Job title partially aligns with a Java/backend role")
    elif contains_phrase(title_norm, "java"):
        title_pts = round(WEIGHTS["title"] * 0.4)
    elif any(w in title_norm for w in ("full stack", "fullstack", "backend", "integration")) and (
        contains_phrase(haystack, "java") or contains_phrase(haystack, "spring boot")
    ):
        # Title doesn't say "Java" explicitly, but is a backend/full-stack/
        # integration role whose body confirms a Java/Spring stack (e.g.
        # "Full Stack Developer" - Java, Spring Boot, Angular, PostgreSQL).
        title_pts = round(WEIGHTS["title"] * 0.55)
        reasons.append("Role type aligns with backend/full-stack profile, confirmed Java/Spring in requirements")
    else:
        title_pts = 0

    # --- 2. Core skills / Tier 1 (30 pts) ---
    tier1_hits = count_hits(haystack, TIER1_SKILLS)
    core_pts = round(WEIGHTS["core_skills"] * min(1.0, len(tier1_hits) / 6))
    if tier1_hits:
        reasons.append(f"Strong direct experience overlap: {', '.join(tier1_hits[:5])}")

    # --- 3. Architecture (15 pts) ---
    arch_pts, arch_hits = _weighted(haystack, ARCHITECTURE_KEYWORDS, WEIGHTS["architecture"])
    if arch_hits:
        reasons.append("Strong event-driven / microservices architecture match")

    # --- 4. Messaging (10 pts) ---
    msg_pts, msg_hits = _weighted(haystack, MESSAGING_KEYWORDS, WEIGHTS["messaging"])
    if msg_hits:
        reasons.append(f"Messaging/event-streaming overlap: {', '.join(msg_hits)}")

    # --- 5. Database (5 pts) ---
    db_pts, db_hits = _weighted(haystack, DATABASE_KEYWORDS, WEIGHTS["database"])

    # --- 6. Security (5 pts) ---
    sec_pts, sec_hits = _weighted(haystack, SECURITY_KEYWORDS, WEIGHTS["security"])

    # --- 7. DevOps (5 pts) ---
    devops_pts, devops_hits = _weighted(haystack, DEVOPS_KEYWORDS, WEIGHTS["devops"])

    score = min(100, title_pts + core_pts + arch_pts + msg_pts + db_pts + sec_pts + devops_pts)
    level, emoji = _match_level(score)

    # --- Matched / Partial / Missing skill breakdown ---
    tier2_hits = count_hits(haystack, TIER2_SKILLS)
    tier3_hits = count_hits(haystack, TIER3_SKILLS)

    matched_skills = sorted(set(tier1_hits + tier2_hits))
    partial_skills = sorted(set(tier3_hits))

    notable_hits = set(count_hits(haystack, NOTABLE_JOB_SKILLS))
    known_skills = set(tier1_hits) | set(tier2_hits) | set(tier3_hits)
    missing_skills = sorted(notable_hits - known_skills)

    if not reasons:
        reasons.append("Limited overlap detected between job requirements and current CV profile")

    return CVMatchResult(
        score=score,
        level=level,
        emoji=emoji,
        matched_skills=matched_skills,
        partial_skills=partial_skills,
        missing_skills=missing_skills,
        reasons=reasons,
    )
