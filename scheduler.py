"""
JobSnipr — Persistent Group Scheduler
Delayed group delivery must survive restarts, crashes, and redeploys.
Instead of threading.Timer (which is purely in-memory and lost on
restart), every scheduled group message is a row in SQLite. On every
tick we ask the database which messages are due and send those — so a
message scheduled 25 minutes before a crash is still sent 5 minutes
after the process comes back up.
"""

from __future__ import annotations

from database import Database
from telegram_client import TelegramClient
from utils.logging_setup import get_logger

log = get_logger()


class GroupScheduler:
    def __init__(self, db: Database, telegram: TelegramClient, group_chat_id: str) -> None:
        self._db = db
        self._telegram = telegram
        self._group_chat_id = group_chat_id

    def recover_on_startup(self) -> None:
        pending = self._db.count_pending_messages()
        if pending:
            log.info(f"[scheduler] recovered {pending} pending group message(s) from previous run")
        else:
            log.info("[scheduler] no pending group messages to recover")

    def tick(self) -> None:
        """Send every scheduled message whose time has come. Safe to
        call repeatedly (e.g. every SCHEDULER_TICK_SECONDS)."""
        due = self._db.get_due_messages(limit=20)
        for row in due:
            message_id = row["id"]
            fingerprint = row["job_fingerprint"]
            text = row["message"]

            ok = self._telegram.send(self._group_chat_id, text)
            if ok:
                self._db.mark_message_sent(message_id)
                self._db.mark_group_sent(fingerprint)
                log.info(f"[telegram] group sent fingerprint={fingerprint}")
            else:
                self._db.bump_message_attempts(message_id)
                log.warning(f"[telegram] group send failed, will retry fingerprint={fingerprint}")
