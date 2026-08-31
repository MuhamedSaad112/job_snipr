"""
JobSnipr — Skill Taxonomy
Structured, weighted, alias-aware technology taxonomy for the Java /
Backend / Integration ecosystem. This module is pure data + small
matching helpers; scoring logic lives in domain_matcher.py and
cv_matcher.py so the taxonomy itself stays reusable and easy to extend.
"""

from __future__ import annotations

import re

# ══════════════════════════════════════════════════════════════════
#  ALIASES — normalize noisy real-world phrasing to canonical terms
# ══════════════════════════════════════════════════════════════════

ALIASES: dict[str, str] = {
    "springboot": "spring boot",
    "spring-boot": "spring boot",
    "micro-service": "microservice",
    "micro services": "microservices",
    "microservices architecture": "microservices",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "j2ee": "enterprise java",
    "java ee": "enterprise java",
    "jakarta ee": "enterprise java",
    "restful": "rest api",
    "rest apis": "rest api",
    "event-driven": "event driven",
    "event-driven architecture": "event driven architecture",
    "fullstack": "full stack",
    "full-stack": "full stack",
    "ci cd": "ci/cd",
    "ci-cd": "ci/cd",
    "back-end": "backend",
    "back end": "backend",
    "node js": "node.js",
    "dot net": ".net",
}

_WS_RE = re.compile(r"\s+")
_HYPHEN_RE = re.compile(r"[-_]")


def normalize_text(text: str) -> str:
    """Lowercase, normalize whitespace/hyphens, apply alias substitution.
    Preserves meaningful symbols like C#, .NET, C++ by only collapsing
    hyphens/underscores that sit between word characters (not inside
    tokens like 'node.js' which contain no hyphen anyway)."""
    if not text:
        return ""
    t = text.lower()
    t = _HYPHEN_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    for alias, canonical in ALIASES.items():
        if alias in t:
            t = t.replace(alias, canonical)
    return t


def contains_phrase(haystack: str, phrase: str) -> bool:
    """Word-boundary-safe substring check. Prevents 'java' from
    matching inside 'javascript'."""
    pattern = r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])"
    return re.search(pattern, haystack) is not None


def count_hits(haystack: str, phrases: list[str]) -> list[str]:
    """Return the list of distinct phrases found in haystack (each
    phrase counted at most once, regardless of repetition in text)."""
    return [p for p in phrases if contains_phrase(haystack, p)]


# ══════════════════════════════════════════════════════════════════
#  STRONG JAVA/BACKEND TITLE PHRASES (used for RULE A / title bonus)
# ══════════════════════════════════════════════════════════════════

STRONG_TITLE_PHRASES = [
    "java developer", "java engineer", "java backend developer",
    "java backend engineer", "java software engineer",
    "senior java developer", "senior java engineer", "lead java developer",
    "principal java engineer", "java architect", "java technical lead",
    "enterprise java developer", "enterprise java engineer",
    "spring boot developer", "spring boot engineer", "spring developer",
    "spring engineer", "backend developer", "backend engineer",
    "backend software engineer", "senior backend engineer",
    "server side developer", "server side engineer",
    "software engineer backend", "microservices engineer",
    "microservices developer", "kafka developer", "kafka engineer",
    "integration engineer", "integration developer", "integration architect",
    "enterprise integration engineer", "system integration engineer",
    "api integration engineer", "backend integration engineer",
    "middleware engineer", "middleware developer",
    "java full stack developer", "full stack java developer",
    "java fullstack developer", "fullstack java developer",
    "java full stack engineer",
]

INTEGRATION_TITLE_PHRASES = [
    "integration engineer", "integration developer", "integration architect",
    "enterprise integration engineer", "enterprise integration developer",
    "system integration engineer", "system integration developer",
    "application integration engineer", "api integration engineer",
    "backend integration engineer", "middleware engineer",
    "middleware developer",
]

BACKEND_TITLE_PHRASES = [
    "backend developer", "backend engineer", "backend software engineer",
    "senior backend engineer", "backend architect",
    "backend technical lead", "server side developer",
    "server side engineer", "software engineer backend",
    "platform backend engineer",
]

JAVA_FULLSTACK_TITLE_PHRASES = [
    "java full stack developer", "java fullstack developer",
    "full stack java developer", "fullstack java developer",
    "java full stack engineer", "spring boot full stack developer",
]

# ══════════════════════════════════════════════════════════════════
#  SCORING CATEGORIES (weight = max points contributed to DOMAIN_SCORE)
# ══════════════════════════════════════════════════════════════════

CATEGORIES: dict[str, dict] = {
    "core_java": {
        "weight": 25,
        "keywords": [
            "java", "java se", "core java", "advanced java", "jvm",
            "java 8", "java 11", "java 17", "java 21", "java 22", "java 23",
            "enterprise java", "multithreading", "concurrency",
            "java concurrency", "completablefuture", "executorservice",
            "virtual threads", "project loom", "streams api", "java streams",
            "generics", "collections framework", "garbage collection",
            "gc tuning", "jvm tuning", "maven", "gradle", "junit",
            "junit 5", "mockito", "testcontainers", "kotlin", "scala",
        ],
    },
    "spring": {
        "weight": 20,
        "keywords": [
            "spring", "spring framework", "spring boot", "spring mvc",
            "spring web", "spring webflux", "spring reactive", "spring data",
            "spring data jpa", "spring jpa", "spring orm", "spring security",
            "spring cloud", "spring batch", "spring integration",
            "spring amqp", "spring kafka", "spring retry", "spring cache",
            "spring session", "spring aop", "spring cloud gateway",
            "spring cloud config", "eureka", "openfeign", "feign client",
            "resilience4j", "circuit breaker", "hystrix", "spring native",
            "project reactor", "mono", "flux",
        ],
    },
    "backend_context": {
        "weight": 20,
        "keywords": BACKEND_TITLE_PHRASES + [
            "backend", "rest api", "api developer", "api engineer",
            "restful services", "web services", "backend services",
            "enterprise software engineer", "enterprise application developer",
            "enterprise backend engineer", "server side",
        ],
    },
    "microservices": {
        "weight": 15,
        "keywords": [
            "microservice", "microservices", "service oriented architecture",
            "soa", "distributed systems", "distributed system",
            "distributed architecture", "cloud native architecture",
            "api gateway", "service discovery", "service registry",
            "circuit breaker", "bulkhead pattern", "saga pattern", "saga",
            "cqrs", "event sourcing", "strangler pattern",
            "backend for frontend", "domain driven design", "ddd",
            "distributed tracing", "high availability", "horizontal scaling",
        ],
    },
    "messaging": {
        "weight": 15,
        "keywords": [
            "kafka", "apache kafka", "kafka streams", "kafka connect",
            "kafka consumer", "kafka producer", "confluent kafka",
            "confluent platform", "schema registry", "activemq",
            "apache activemq", "rabbitmq", "ibm mq", "apache pulsar",
            "pulsar", "jms", "java message service", "message queue",
            "message broker", "message bus", "enterprise messaging",
            "publish subscribe", "pub sub", "dead letter queue", "dlq",
            "event driven", "event driven architecture", "event streaming",
            "outbox pattern", "transactional outbox", "idempotent consumer",
        ],
    },
    "integration": {
        "weight": 15,
        "keywords": INTEGRATION_TITLE_PHRASES + [
            "spring integration", "apache camel", "camel", "mulesoft",
            "mule esb", "wso2", "boomi", "tibco", "ibm integration bus",
            "iib", "apache nifi", "middleware", "enterprise service bus",
            "esb", "enterprise integration patterns", "eip", "erp integration",
            "sap integration", "system integration", "web services integration",
        ],
    },
    "api_web": {
        "weight": 10,
        "keywords": [
            "rest", "rest api", "restful api", "http api", "soap",
            "wsdl", "openapi", "swagger", "kong", "apigee",
            "api gateway", "api management", "graphql", "graphql api",
        ],
    },
    "database": {
        "weight": 8,
        "keywords": [
            "postgresql", "mysql", "mariadb", "oracle database",
            "sql server", "mongodb", "cassandra", "dynamodb",
            "elasticsearch", "opensearch", "redis", "hibernate",
            "jpa", "jakarta persistence", "spring data jpa", "mybatis",
            "jooq", "sql", "query optimization", "indexing", "transactions",
            "connection pool", "hikaricp", "liquibase", "flyway",
        ],
    },
    "security": {
        "weight": 8,
        "keywords": [
            "spring security", "application security", "api security",
            "jwt", "json web token", "oauth", "oauth2", "openid connect",
            "oidc", "single sign on", "sso", "keycloak", "iam",
            "rbac", "role based access control", "abac", "authentication",
            "authorization", "access control",
        ],
    },
    "cloud_devops": {
        "weight": 6,
        "keywords": [
            "docker", "docker compose", "kubernetes", "openshift", "helm",
            "ci/cd", "continuous integration", "continuous deployment",
            "github actions", "gitlab ci", "jenkins", "argocd",
            "terraform", "ansible", "prometheus", "grafana", "elk stack",
            "elastic stack", "opentelemetry", "jaeger", "zipkin", "aws",
            "azure", "google cloud", "gcp", "cloud native",
        ],
    },
    "java_fullstack": {
        "weight": 12,
        "keywords": JAVA_FULLSTACK_TITLE_PHRASES + [
            "angular", "react", "react.js", "typescript",
        ],
    },
}

# ══════════════════════════════════════════════════════════════════
#  NEGATIVE / EXCLUSION KEYWORDS
#  Titles that indicate an unrelated role UNLESS strong positive
#  evidence (Java/Spring/Backend/Integration) overrides them.
# ══════════════════════════════════════════════════════════════════

EXCLUSION_TITLE_PHRASES = [
    "frontend developer", "frontend engineer", "react developer",
    "vue developer", "ui developer", "ux designer", "ui/ux designer",
    "wordpress developer", "php developer", "laravel developer",
    "mobile developer", "android developer", "ios developer",
    "flutter developer", "react native developer",
    "qa engineer", "manual tester", "automation tester",
    "data analyst", "business analyst", "data scientist",
    "machine learning engineer", "ai engineer", "network engineer",
    "system administrator", "it support", "help desk",
    "cybersecurity analyst", "devops engineer", "cloud engineer",
    "site reliability engineer", "sre",
]

# Technologies that must NOT count toward relevance on their own —
# they only matter in combination with genuine Java/backend context.
CONTEXT_REQUIRED_KEYWORDS = [
    "kubernetes", "docker", "aws", "azure", "gcp", "terraform",
    "kafka", "spark", "airflow", "python", "data engineering",
]

# ══════════════════════════════════════════════════════════════════
#  SENIORITY / JOB TYPE DETECTION
# ══════════════════════════════════════════════════════════════════

SENIORITY_LEVELS: list[tuple[str, list[str]]] = [
    ("Intern/Junior", ["intern", "junior", "graduate", "entry level", "associate"]),
    ("Principal/Architect", ["principal engineer", "principal", "architect", "solution architect", "software architect"]),
    ("Staff", ["staff engineer", "staff"]),
    ("Lead", ["tech lead", "technical lead", "team lead", "lead developer", "lead engineer"]),
    ("Senior", ["senior engineer", "senior developer", "senior"]),
    ("Mid-Level", ["mid-level", "mid level"]),
]

JOB_TYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Contract", ["contract", "contractor"]),
    ("Freelance", ["freelance"]),
    ("Internship", ["internship"]),
    ("Part Time", ["part time", "part-time"]),
    ("Temporary", ["temporary"]),
    ("Full Time", ["full time", "full-time", "permanent"]),
]

WORK_MODE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Remote", ["remote", "work from home", "wfh"]),
    ("Hybrid", ["hybrid"]),
    ("Onsite", ["onsite", "on-site", "on site"]),
]


def detect_seniority(text: str) -> str:
    for label, kws in SENIORITY_LEVELS:
        if any(contains_phrase(text, kw) for kw in kws):
            return label
    return "Not specified"


def detect_job_type(text: str) -> str:
    for label, kws in JOB_TYPE_KEYWORDS:
        if any(contains_phrase(text, kw) for kw in kws):
            return label
    return "Not specified"


def detect_work_mode(text: str) -> str:
    for label, kws in WORK_MODE_KEYWORDS:
        if any(contains_phrase(text, kw) for kw in kws):
            return label
    return "Not specified"


# ══════════════════════════════════════════════════════════════════
#  GULF / MENA LOCATION TAXONOMY
# ══════════════════════════════════════════════════════════════════

LOCATION_KEYWORDS: dict[str, list[str]] = {
    "🇸🇦": ["saudi", "ksa", "riyadh", "jeddah", "dammam", "khobar",
             "dhahran", "neom", "tabuk", "makkah", "mecca", "madinah",
             "medina", "saudi arabia"],
    "🇦🇪": ["uae", "dubai", "abu dhabi", "sharjah", "ajman",
             "united arab emirates"],
    "🇶🇦": ["qatar", "doha"],
    "🇰🇼": ["kuwait", "kuwait city"],
    "🇧🇭": ["bahrain", "manama"],
    "🇴🇲": ["oman", "muscat"],
    "🇪🇬": ["egypt", "cairo"],
    "🌍": ["remote", "worldwide", "global", "anywhere", "emea", "mena"],
}

ALL_LOCATION_KEYWORDS = [kw for kws in LOCATION_KEYWORDS.values() for kw in kws]


def location_flag(location_text: str) -> str:
    norm = normalize_text(location_text)
    for flag, kws in LOCATION_KEYWORDS.items():
        if flag == "🌍":
            continue
        if any(kw in norm for kw in kws):
            return flag
    if any(kw in norm for kw in LOCATION_KEYWORDS["🌍"]):
        return "🌍"
    return "🌐"


def is_target_location(location_text: str, country_text: str = "") -> bool:
    norm = normalize_text(f"{location_text} {country_text}")
    return any(kw in norm for kw in ALL_LOCATION_KEYWORDS)
