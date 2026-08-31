"""
JobSnipr — Persistence (SQLite)
Replaces the old JSON-only seen-jobs file. Everything the app needs to
survive a restart lives here: discovered jobs, delayed group-delivery
scheduling, and per-source health tracking.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from utils.logging_setup import get_logger

log = get_logger()

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint     TEXT UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    company         TEXT NOT NULL,
    location        TEXT,
    url             TEXT NOT NULL,
    source          TEXT,
    description     TEXT,
    tags            TEXT,
    domain_score    INTEGER DEFAULT 0,
    cv_score        INTEGER DEFAULT 0,
    priority        TEXT,
    discovered_at   TEXT NOT NULL,
    personal_sent   INTEGER DEFAULT 0,
    group_sent      INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs(fingerprint);

CREATE TABLE IF NOT EXISTS scheduled_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_fingerprint TEXT NOT NULL,
    message         TEXT NOT NULL,
    destination     TEXT NOT NULL,
    scheduled_at    TEXT NOT NULL,
    sent            INTEGER DEFAULT 0,
    attempts        INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sched_due ON scheduled_messages(sent, scheduled_at);

CREATE TABLE IF NOT EXISTS sources_health (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name     TEXT UNIQUE NOT NULL,
    last_success    TEXT,
    last_error      TEXT,
    jobs_found      INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'unknown'
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Thread-safe SQLite wrapper. One connection, guarded by a lock —
    the app's traffic is low-volume enough that this is simpler and
    safer than a connection pool, and SQLite serializes writes anyway."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)
        log.info("[db] schema initialized")

    @contextmanager
    def _cursor(self):
        with self._lock:
            cur = self._conn.cursor()
            try:
                yield cur
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            finally:
                cur.close()

    # ────────────────────────────────────────────────────────────
    #  JOBS
    # ────────────────────────────────────────────────────────────

    def job_exists(self, fingerprint: str) -> bool:
        with self._cursor() as cur:
            cur.execute("SELECT 1 FROM jobs WHERE fingerprint = ?", (fingerprint,))
            return cur.fetchone() is not None

    def insert_job(
        self,
        fingerprint: str,
        title: str,
        company: str,
        location: str,
        url: str,
        source: str,
        description: str,
        tags: str,
        domain_score: int,
        cv_score: int,
        priority: str,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT OR IGNORE INTO jobs
                (fingerprint, title, company, location, url, source, description,
                 tags, domain_score, cv_score, priority, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (fingerprint, title, company, location, url, source, description,
                 tags, domain_score, cv_score, priority, _now()),
            )

    def mark_personal_sent(self, fingerprint: str) -> None:
        with self._cursor() as cur:
            cur.execute("UPDATE jobs SET personal_sent = 1 WHERE fingerprint = ?", (fingerprint,))

    def mark_group_sent(self, fingerprint: str) -> None:
        with self._cursor() as cur:
            cur.execute("UPDATE jobs SET group_sent = 1 WHERE fingerprint = ?", (fingerprint,))

    # ────────────────────────────────────────────────────────────
    #  SCHEDULED MESSAGES (persistent delayed group delivery)
    # ────────────────────────────────────────────────────────────

    def schedule_message(self, job_fingerprint: str, message: str, destination: str, scheduled_at: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO scheduled_messages
                (job_fingerprint, message, destination, scheduled_at, sent, attempts, created_at)
                VALUES (?, ?, ?, ?, 0, 0, ?)
                """,
                (job_fingerprint, message, destination, scheduled_at, _now()),
            )

    def get_due_messages(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT * FROM scheduled_messages
                WHERE sent = 0 AND scheduled_at <= ?
                ORDER BY scheduled_at ASC
                LIMIT ?
                """,
                (_now(), limit),
            )
            return cur.fetchall()

    def count_pending_messages(self) -> int:
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM scheduled_messages WHERE sent = 0")
            return cur.fetchone()["c"]

    def mark_message_sent(self, message_id: int) -> None:
        with self._cursor() as cur:
            cur.execute("UPDATE scheduled_messages SET sent = 1 WHERE id = ?", (message_id,))

    def bump_message_attempts(self, message_id: int) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE scheduled_messages SET attempts = attempts + 1 WHERE id = ?",
                (message_id,),
            )

    # ────────────────────────────────────────────────────────────
    #  SOURCE HEALTH
    # ────────────────────────────────────────────────────────────

    def record_source_success(self, source_name: str, jobs_found: int) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO sources_health (source_name, last_success, jobs_found, status)
                VALUES (?, ?, ?, 'ok')
                ON CONFLICT(source_name) DO UPDATE SET
                    last_success = excluded.last_success,
                    jobs_found = excluded.jobs_found,
                    status = 'ok'
                """,
                (source_name, _now(), jobs_found),
            )

    def record_source_failure(self, source_name: str, error: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO sources_health (source_name, last_error, status)
                VALUES (?, ?, 'error')
                ON CONFLICT(source_name) DO UPDATE SET
                    last_error = excluded.last_error,
                    status = 'error'
                """,
                (source_name, json.dumps(str(error))[:500]),
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
