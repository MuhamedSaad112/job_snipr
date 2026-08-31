"""
JobSnipr — Configuration
Centralized environment-based configuration. No hardcoded secrets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    # --- Required ---
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    personal_chat_id: str = field(default_factory=lambda: os.getenv("PERSONAL_CHAT_ID", ""))
    group_chat_id: str = field(default_factory=lambda: os.getenv("GROUP_CHAT_ID", ""))

    # --- Optional identity ---
    service_name: str = field(default_factory=lambda: os.getenv("SERVICE_NAME", "jobsnipr"))

    # --- Optional API keys ---
    adzuna_app_id: str = field(default_factory=lambda: os.getenv("ADZUNA_APP_ID", ""))
    adzuna_api_key: str = field(default_factory=lambda: os.getenv("ADZUNA_API_KEY", ""))
    jsearch_key: str = field(default_factory=lambda: os.getenv("JSEARCH_KEY", ""))

    # --- Timing ---
    group_delay_minutes: int = field(default_factory=lambda: _int_env("GROUP_DELAY_MINUTES", 30))
    poll_interval_seconds: int = field(default_factory=lambda: _int_env("POLL_INTERVAL_SECONDS", 300))
    scheduler_tick_seconds: int = field(default_factory=lambda: _int_env("SCHEDULER_TICK_SECONDS", 30))
    telegram_send_delay_seconds: float = field(default_factory=lambda: _float_env("TELEGRAM_SEND_DELAY_SECONDS", 1.5))

    # --- Relevance / matching ---
    min_domain_score: int = field(default_factory=lambda: _int_env("MIN_DOMAIN_SCORE", 45))

    # --- Storage ---
    database_path: str = field(default_factory=lambda: os.getenv("DATABASE_PATH", "jobsnipr.db"))

    # --- Logging ---
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: str = field(default_factory=lambda: os.getenv("LOG_FILE", "jobsnipr.log"))

    # --- HTTP ---
    http_connect_timeout: float = field(default_factory=lambda: _float_env("HTTP_CONNECT_TIMEOUT", 6.0))
    http_read_timeout: float = field(default_factory=lambda: _float_env("HTTP_READ_TIMEOUT", 20.0))
    http_max_retries: int = field(default_factory=lambda: _int_env("HTTP_MAX_RETRIES", 3))

    def validate(self) -> list[str]:
        """Return a list of human-readable problems with the current config."""
        problems = []
        if not self.bot_token:
            problems.append("BOT_TOKEN is not set")
        if not self.personal_chat_id:
            problems.append("PERSONAL_CHAT_ID is not set")
        if not self.group_chat_id:
            problems.append("GROUP_CHAT_ID is not set")
        return problems


settings = Settings()
