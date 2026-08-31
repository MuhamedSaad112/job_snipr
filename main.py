"""
JobSnipr — Smart Java, Backend & Integration Job Discovery
Main orchestration: fetch → normalize → validate → domain filter →
dedupe → CV match → send personal immediately → schedule delayed
group delivery (persisted in SQLite, survives restarts).
"""

from __future__ import annotations

import signal
import sys
import time
from datetime import datetime, timedelta, timezone

from config import settings
from cv_matcher import compute_cv_match
from database import Database
from deduplicator import compute_fingerprint, source_quality_for
from domain_matcher import classify_tracks, compute_domain_score
from models import ProcessedJob
from normalizer import compute_freshness, compute_priority, normalize_job
from scheduler import GroupScheduler
from sources import SOURCE_REGISTRY
from taxonomy import detect_job_type, detect_seniority, is_target_location
from telegram_client import TelegramClient, format_group_message, format_personal_message
from utils.http_client import HttpClient
from utils.logging_setup import setup_logging

log = setup_logging(level=settings.log_level, log_file=settings.log_file)

_shutdown_requested = False


def _handle_signal(signum, frame) -> None:
    global _shutdown_requested
    log.info(f"[main] received signal {signum}, shutting down gracefully...")
    _shutdown_requested = True


def process_source(name: str, fetch_fn, http: HttpClient, db: Database) -> list:
    """Fetch + normalize a single source. Failures here are isolated —
    a broken source logs and returns an empty list, never crashes the
    poll loop."""
    try:
        raw_items = fetch_fn(http)
        db.record_source_success(name, len(raw_items))
        log.info(f"[source:{name}] {len(raw_items)} jobs fetched")
        return raw_items
    except Exception as exc:
        db.record_source_failure(name, str(exc))
        log.error(f"[source:{name}] failed: {exc}")
        return []


def build_processed_job(raw_dict: dict, source_quality: int) -> ProcessedJob | None:
    raw = normalize_job(raw_dict)
    if raw is None:
        log.debug("[job] rejected reason=missing_required_fields")
        return None
    raw.source_quality = source_quality

    domain = compute_domain_score(raw.title, raw.description, raw.tags, raw.category)
    if not domain.accepted:
        log.info(f"[job] rejected reason=domain_relevance title={raw.title!r} score={domain.score}")
        return None
    if domain.score < settings.min_domain_score:
        log.info(f"[job] rejected reason=below_min_score title={raw.title!r} score={domain.score}")
        return None

    fingerprint = compute_fingerprint(raw.title, raw.company, raw.location)

    cv = compute_cv_match(raw.title, raw.description, raw.tags)
    tracks = classify_tracks(domain, raw.title, raw.description)
    freshness = compute_freshness(raw.posted_date)
    target_loc = is_target_location(raw.location, raw.country)
    priority = compute_priority(cv.score, domain.score, raw.source_quality, target_loc, freshness)
    seniority = detect_seniority(f"{raw.title} {raw.description}")
    job_type = detect_job_type(f"{raw.title} {raw.description}")

    log.info(
        f"[job] relevance_score={domain.score} cv_score={cv.score} "
        f"title={raw.title!r} tracks={tracks}"
    )

    return ProcessedJob(
        raw=raw,
        fingerprint=fingerprint,
        domain=domain,
        cv_match=cv,
        priority=priority,
        seniority=seniority,
        job_type=job_type,
        tracks=tracks,
    )


def handle_job(job: ProcessedJob, db: Database, telegram: TelegramClient) -> None:
    if db.job_exists(job.fingerprint):
        log.info(f"[job] duplicate detected fingerprint={job.fingerprint} title={job.raw.title!r}")
        return

    db.insert_job(
        fingerprint=job.fingerprint,
        title=job.raw.title,
        company=job.raw.company,
        location=job.raw.location,
        url=job.raw.url,
        source=job.raw.source,
        description=job.raw.description,
        tags=job.raw.tags,
        domain_score=job.domain.score,
        cv_score=job.cv_match.score,
        priority=job.priority,
    )

    # --- Personal chat: immediate, with full CV analysis ---
    personal_text = format_personal_message(job)
    if telegram.send(settings.personal_chat_id, personal_text):
        db.mark_personal_sent(job.fingerprint)
        log.info(f"[telegram] personal sent title={job.raw.title!r} cv_score={job.cv_match.score}")
    else:
        log.error(f"[telegram] personal send FAILED title={job.raw.title!r}")

    # --- Group: clean message, persisted delay so it survives restarts ---
    group_text = format_group_message(job)
    scheduled_at = (
        datetime.now(timezone.utc) + timedelta(minutes=settings.group_delay_minutes)
    ).isoformat()
    db.schedule_message(
        job_fingerprint=job.fingerprint,
        message=group_text,
        destination="group",
        scheduled_at=scheduled_at,
    )
    log.info(f"[telegram] group scheduled title={job.raw.title!r} at={scheduled_at}")


def poll_once(db: Database, telegram: TelegramClient, http: HttpClient) -> None:
    for name, fetch_fn in SOURCE_REGISTRY:
        raw_items = process_source(name, fetch_fn, http, db)
        for raw_dict in raw_items:
            source_quality = source_quality_for(raw_dict.get("source", name))
            job = build_processed_job(raw_dict, source_quality)
            if job is not None:
                handle_job(job, db, telegram)


def main() -> int:
    problems = settings.validate()
    if problems:
        for p in problems:
            log.error(f"[config] {p}")
        log.error("[main] cannot start — fix configuration and retry")
        return 1

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    db = Database(settings.database_path)
    http = HttpClient(
        connect_timeout=settings.http_connect_timeout,
        read_timeout=settings.http_read_timeout,
        max_retries=settings.http_max_retries,
    )
    telegram = TelegramClient(
        bot_token=settings.bot_token,
        http=http,
        send_delay_seconds=settings.telegram_send_delay_seconds,
    )
    group_scheduler = GroupScheduler(db, telegram, settings.group_chat_id)

    telegram.send_startup(settings.service_name, settings.personal_chat_id)
    group_scheduler.recover_on_startup()

    log.info(
        f"[main] JobSnipr started — poll_interval={settings.poll_interval_seconds}s "
        f"group_delay={settings.group_delay_minutes}min min_domain_score={settings.min_domain_score}"
    )

    last_poll = 0.0
    try:
        while not _shutdown_requested:
            now = time.time()
            if now - last_poll >= settings.poll_interval_seconds:
                try:
                    poll_once(db, telegram, http)
                except Exception as exc:
                    log.error(f"[main] poll cycle error: {exc}", exc_info=True)
                last_poll = now

            group_scheduler.tick()
            time.sleep(settings.scheduler_tick_seconds)
    finally:
        telegram.send_shutdown(settings.service_name, settings.personal_chat_id)
        db.close()
        log.info("[main] shutdown complete")

    return 0


if __name__ == "__main__":
    sys.exit(main())
