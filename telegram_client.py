"""
JobSnipr — Telegram Client
Handles both destinations (personal chat + group), message formatting,
HTML escaping, and flood-safe sending with retry/backoff. A job is only
ever marked as sent after Telegram confirms success.
"""

from __future__ import annotations

import time

from models import CVMatchResult, ProcessedJob
from normalizer import escape_html
from taxonomy import location_flag
from utils.http_client import HttpClient
from utils.logging_setup import get_logger

log = get_logger()

STARTUP_MESSAGE = (
    "بِسْمِ اللهِ الرَّحْمٰنِ الرَّحِيمِ 🌿\n"
    "اللَّهُمَّ صَلِّ عَلَىٰ مُحَمَّدٍ ﷺ 🤍\n"
    "أَسْتَغْفِرُ اللَّهَ الْعَظِيمَ وَأَتُوبُ إِلَيْهِ 🤲\n\n"
    "✅ <b>JobSnipr</b> started successfully\n"
    "Service: {service_name}\n"
    "Smart Java, Backend &amp; Integration Job Discovery 🚀"
)

SHUTDOWN_MESSAGE = (
    "بِسْمِ اللهِ الرَّحْمٰنِ الرَّحِيمِ 🌿\n"
    "اللَّهُمَّ صَلِّ عَلَىٰ مُحَمَّدٍ ﷺ 🤍\n"
    "أَسْتَغْفِرُ اللَّهَ الْعَظِيمَ وَأَتُوبُ إِلَيْهِ 🤲\n\n"
    "🛑 <b>JobSnipr</b> stopped\n"
    "Service: {service_name}"
)


class TelegramClient:
    def __init__(self, bot_token: str, http: HttpClient, send_delay_seconds: float = 1.5) -> None:
        self._bot_token = bot_token
        self._http = http
        self._send_delay = send_delay_seconds
        self._api_base = f"https://api.telegram.org/bot{bot_token}"

    def send(self, chat_id: str, text: str) -> bool:
        """Send a message; returns True only on confirmed Telegram success."""
        if not self._bot_token or not chat_id:
            log.error("[telegram] missing bot token or chat id — cannot send")
            return False

        url = f"{self._api_base}/sendMessage"
        max_attempts = 4
        backoff = 2.0

        for attempt in range(1, max_attempts + 1):
            resp = self._http.post_json(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
            )
            if resp is None:
                log.warning(f"[telegram] send attempt {attempt} network error, chat={chat_id}")
            elif resp.status_code == 200:
                time.sleep(self._send_delay)  # flood protection between messages
                return True
            elif resp.status_code == 429:
                retry_after = 5
                try:
                    retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
                except Exception:
                    pass
                log.warning(f"[telegram] rate limited, retry_after={retry_after}s")
                time.sleep(retry_after)
                continue
            else:
                log.warning(f"[telegram] send failed status={resp.status_code} body={resp.text[:200]}")

            if attempt < max_attempts:
                time.sleep(backoff)
                backoff *= 2

        log.error(f"[telegram] all send attempts failed, chat={chat_id}")
        return False

    def send_startup(self, service_name: str, personal_chat_id: str) -> None:
        self.send(personal_chat_id, STARTUP_MESSAGE.format(service_name=service_name))

    def send_shutdown(self, service_name: str, personal_chat_id: str) -> None:
        self.send(personal_chat_id, SHUTDOWN_MESSAGE.format(service_name=service_name))


# ══════════════════════════════════════════════════════════════════
#  MESSAGE FORMATTING
# ══════════════════════════════════════════════════════════════════

def format_personal_message(job: ProcessedJob) -> str:
    raw = job.raw
    cv: CVMatchResult = job.cv_match
    flag = location_flag(raw.location or raw.country)

    matched = "\n".join(f"• {escape_html(s.title())}" for s in cv.matched_skills[:8]) or "• —"
    missing = "\n".join(f"• {escape_html(s.title())}" for s in cv.missing_skills[:6])
    reasons = " ".join(cv.reasons[:2])

    lines = [
        f"{cv.emoji} <b>NEW JOB MATCH</b>",
        "",
        f"📌 <b>{escape_html(raw.title)}</b>",
        f"🏢 {escape_html(raw.company)}",
        f"{flag} {escape_html(raw.location or 'Not specified')}",
        f"🌐 {escape_html(raw.source)}",
    ]
    if raw.salary:
        lines.append(f"💰 {escape_html(raw.salary)}")
    lines.append(f"{job.priority}")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"🎯 <b>CV MATCH: {cv.score}%</b>")
    lines.append(f"{cv.emoji} {cv.level}")
    lines.append("")
    lines.append("✅ <b>Matching Skills:</b>")
    lines.append(matched)
    lines.append("")
    lines.append(f"💡 <b>Why it matches:</b>\n{escape_html(reasons)}")
    if missing:
        lines.append("")
        lines.append("⚠️ <b>Missing / Preferred Skills:</b>")
        lines.append(missing)
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"🔗 <b>Apply:</b>\n{escape_html(raw.url)}")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("🤖 <i>JobSnipr Smart Match</i>")

    return "\n".join(lines)


def format_group_message(job: ProcessedJob) -> str:
    raw = job.raw
    flag = location_flag(raw.location or raw.country)
    tags_display = " | ".join(job.tracks[:5]) if job.tracks else escape_html(raw.tags[:80])

    lines = [
        "🔥 <b>NEW JOB ALERT</b>",
        "",
        f"💼 <b>{escape_html(raw.title)}</b>",
        f"🏢 {escape_html(raw.company)}",
        f"{flag} {escape_html(raw.location or 'Not specified')}",
    ]
    if tags_display:
        lines.append(f"🏷 {escape_html(tags_display)}")
    lines.append("")
    lines.append(f"🌐 Source: {escape_html(raw.source)}")
    lines.append("")
    lines.append(f"🔗 <b>Apply Now:</b>\n{escape_html(raw.url)}")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("🤖 <b>JobSnipr</b>")
    lines.append("Java • Backend • Microservices • Integration")

    return "\n".join(lines)
