# JobSnipr

**Smart Java, Backend & Integration Job Discovery**

JobSnipr is a domain-aware job aggregation and matching system focused
on the Java Backend / Spring Boot / Microservices / Integration
ecosystem in the Gulf, MENA and remote markets. It replaces naive
`if keyword in text` filtering with a weighted, explainable relevance
and CV-matching engine, and delivers to two Telegram destinations with
different levels of detail.

## Architecture

```
project/
├── main.py              # orchestration loop, signal handling
├── config.py             # env-based configuration
├── database.py            # SQLite persistence (jobs, scheduling, source health)
├── models.py               # dataclasses: RawJob, DomainScore, CVMatchResult, ProcessedJob
├── normalizer.py            # field validation, HTML escaping, freshness, priority
├── taxonomy.py                # skill categories, aliases, seniority/location detection
├── domain_matcher.py            # weighted domain relevance engine (rules A-D)
├── cv_matcher.py                  # explainable CV match scoring (0-100)
├── deduplicator.py                  # fuzzy fingerprint dedup, source quality
├── scheduler.py                       # persistent delayed group delivery
├── telegram_client.py                   # sending, formatting, retry/backoff
├── sources/                               # one module per job source
│   ├── base.py                              # shared contract + JSON-LD helper
│   ├── linkedin.py, bayt.py, naukrigulf.py, ...
│   └── __init__.py                            # SOURCE_REGISTRY
├── utils/
│   ├── logging_setup.py                         # rotating file + console logs
│   └── http_client.py                             # pooled Session, retries, timeouts
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

### Flow

```
Job Sources (15 modular sources)
     │
     ▼
Normalization  (normalizer.normalize_job)
     │
     ▼
Validation  (required fields: title, company, url)
     │
     ▼
Domain Relevance Filter  (domain_matcher — weighted categories + rules A-D)
     │  reject → logged, dropped
     ▼
Smart Deduplication  (deduplicator — fingerprint on normalized title+company+location)
     │  duplicate → logged, dropped
     ▼
CV Matching Engine  (cv_matcher — 0-100 explainable score)
     │
     ├──► Send immediately to PERSONAL_CHAT_ID  (full CV analysis)
     │
     └──► Persist row in scheduled_messages (SQLite)
                │
                ▼
          GroupScheduler.tick()  every SCHEDULER_TICK_SECONDS
                │  scheduled_at <= now?
                ▼
          Send to GROUP_CHAT_ID  (clean, no personal data)
```

## How the CV Match percentage is calculated

`cv_matcher.compute_cv_match()` is a **weighted, capped, explainable**
formula — never a random number:

| Category      | Weight |
|---------------|-------:|
| Job Title Match | 30 |
| Core Skills (Tier 1: Java, Spring Boot, Kafka, PostgreSQL, Docker, JWT, RBAC, …) | 30 |
| Architecture (Microservices, DDD, Event-Driven, Distributed Systems) | 15 |
| Messaging (Kafka, ActiveMQ, RabbitMQ, DLQ, Outbox) | 10 |
| Database (PostgreSQL, Redis, JPA, Hibernate, Liquibase) | 5 |
| Security (JWT, OAuth2, RBAC, Keycloak) | 5 |
| DevOps (Docker, CI/CD, GitLab CI, GitHub Actions) | 5 |

Each category counts a **skill at most once** regardless of how many
times it appears in the posting — repeating "Java" ten times cannot
inflate the score. The result is a structured object:

```json
{
  "score": 92,
  "level": "Excellent Match",
  "matched_skills": ["Java", "Spring Boot", "Kafka", "Microservices"],
  "partial_skills": ["Kubernetes"],
  "missing_skills": ["AWS"],
  "reasons": ["Strong Java backend alignment", "..."]
}
```

`matched_skills` come from CV Tier 1/2 (real hands-on experience),
`partial_skills` from Tier 3 (familiar/adjacent — e.g. Kubernetes,
AWS, Angular), and `missing_skills` are named technologies the job
asks for that don't appear anywhere in the CV profile at all. Generic
soft-skill phrases ("team player", "communication") are never treated
as technical requirements.

Domain relevance (whether a job qualifies at all) is a **separate**
0-100 score computed in `domain_matcher.py` from weighted, capped
category hits across Core Java, Spring, Backend, Microservices,
Messaging, Integration, API/Web, Database, Security, Cloud/DevOps and
Java Full Stack — then checked against acceptance rules A-D (relevant
title + score threshold; integration/backend title + 2+ strong techs;
Java Full Stack title + Java/Spring context; enterprise integration
role + relevant integration tech) and an exclusion engine that rejects
generic DevOps/Data-Engineering/Frontend titles unless real Java
evidence overrides them.

## How delayed group delivery survives a restart

Delayed delivery is **never** an in-memory `threading.Timer`. Every
group message is written as a row in the `scheduled_messages` SQLite
table the moment a job is accepted:

```sql
INSERT INTO scheduled_messages (job_fingerprint, message, destination, scheduled_at, sent, ...)
```

The main loop calls `GroupScheduler.tick()` every `SCHEDULER_TICK_SECONDS`
(default 30s), which runs:

```sql
SELECT * FROM scheduled_messages WHERE sent = 0 AND scheduled_at <= now() ORDER BY scheduled_at ASC LIMIT 20
```

and sends whatever is due. Because the schedule lives in the database
file (not process memory), a crash, `SIGTERM`, redeploy, or server
reboot changes nothing: on the next start, `GroupScheduler.recover_on_startup()`
logs how many messages are still pending, and the very next `tick()`
call picks up exactly where things left off — a message scheduled 25
minutes before a crash is still delivered 5 minutes after the process
comes back up. A message is only marked `sent = 1` after Telegram
confirms a `200 OK`; failed sends are retried on the next tick with
an incrementing `attempts` counter.

## Setup

### 1. Local run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: BOT_TOKEN, PERSONAL_CHAT_ID, GROUP_CHAT_ID at minimum

python main.py
```

The SQLite database file (`jobsnipr.db` by default) is created
automatically on first run — no manual migration step needed.

### 2. Getting your Telegram IDs

- `BOT_TOKEN`: create a bot via [@BotFather](https://t.me/BotFather), copy the token.
- `PERSONAL_CHAT_ID`: message your bot directly, then call
  `https://api.telegram.org/bot<TOKEN>/getUpdates` and read `message.chat.id`.
- `GROUP_CHAT_ID`: add the bot to your group (as admin, so it can post),
  send any message, then read the same `getUpdates` response — group
  IDs are negative numbers (e.g. `-1001234567890`).

### 3. Railway deployment

1. Push this project to a GitHub repo.
2. On [Railway](https://railway.app), **New Project → Deploy from GitHub repo**.
3. Railway detects the `Dockerfile` automatically.
4. In **Variables**, add at minimum: `BOT_TOKEN`, `PERSONAL_CHAT_ID`, `GROUP_CHAT_ID`.
   Add any optional keys (`ADZUNA_APP_ID`, `JSEARCH_KEY`, etc.) as needed.
5. **Important for persistence:** Railway's filesystem is ephemeral
   across redeploys unless you attach a **Volume**. Add a Volume
   mounted at `/app/data`, and set `DATABASE_PATH=/app/data/jobsnipr.db`
   so the scheduled-message queue and dedup history survive deploys.
6. Deploy. Check the **Deploy Logs** for the `[main] JobSnipr started`
   line and the startup Telegram message in your personal chat.

### 4. Configuration reference

See `.env.example` for the full list. Everything except
`BOT_TOKEN` / `PERSONAL_CHAT_ID` / `GROUP_CHAT_ID` has a sensible
default.

## Extending sources

Add a new file under `sources/`, implement:

```python
def fetch(http: HttpClient) -> list[dict]:
    ...  # return list of normalized dicts (see sources/base.py)
```

then register it in `sources/__init__.py`'s `SOURCE_REGISTRY`. A
broken or rate-limited source only affects itself — failures are
caught and logged per-source in `main.process_source()`, and recorded
in the `sources_health` table.
