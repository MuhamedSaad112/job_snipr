"""
JobSnipr — HTTP Client
A shared, connection-pooled requests.Session with retry/backoff and
separate connect/read timeouts. Every network source uses this instead
of ad-hoc requests.get() calls, so retry/backoff behavior is consistent
and a single broken source can never hang the whole poll loop.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.logging_setup import get_logger

log = get_logger()

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; JobSnipr/2.0; "
        "+https://github.com/jobsnipr) JavaBackendJobBot"
    ),
    "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
}


class HttpClient:
    """Thin wrapper around a pooled requests.Session."""

    def __init__(
        self,
        connect_timeout: float = 6.0,
        read_timeout: float = 20.0,
        max_retries: int = 3,
    ) -> None:
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.6,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "POST"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy, pool_connections=20, pool_maxsize=20
        )

        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(DEFAULT_HEADERS)

    @property
    def _timeout(self) -> tuple[float, float]:
        return (self._connect_timeout, self._read_timeout)

    def get_json(
        self, url: str, *, headers: dict | None = None, params: dict | None = None
    ) -> Any | None:
        try:
            resp = self.session.get(
                url, headers=headers, params=params, timeout=self._timeout
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            log.warning(f"[http] GET(json) failed url={url[:70]!r} err={exc}")
            return None

    def get_text(
        self, url: str, *, headers: dict | None = None, params: dict | None = None
    ) -> str | None:
        try:
            resp = self.session.get(
                url, headers=headers, params=params, timeout=self._timeout
            )
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            log.warning(f"[http] GET(text) failed url={url[:70]!r} err={exc}")
            return None

    def get_xml(self, url: str, *, headers: dict | None = None) -> ET.Element | None:
        text = self.get_text(url, headers=headers)
        if text is None:
            return None
        try:
            return ET.fromstring(text)
        except ET.ParseError as exc:
            log.warning(f"[http] XML parse failed url={url[:70]!r} err={exc}")
            return None

    def post_json(self, url: str, *, json: dict | None = None) -> Any | None:
        try:
            resp = self.session.post(url, json=json, timeout=self._timeout)
            return resp
        except Exception as exc:
            log.warning(f"[http] POST failed url={url[:70]!r} err={exc}")
            return None
