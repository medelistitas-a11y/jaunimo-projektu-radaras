"""Saugus, mandagus HTTP klientas šaltinių tikrinimui.

- SSRF apsauga per kiekvieną užklausą ir peradresavimą.
- robots.txt laikymasis.
- Vienas užklausų srautas vienam domenui + minimali pauzė tarp užklausų.
- Exponential backoff pakartojimams, ribotas bandymų skaičius, timeout.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.crawler.robots import RobotsCache
from app.crawler.ssrf_guard import SsrfBlockedError, check_url_allowed

logger = logging.getLogger("app.crawler.http_client")


class RobotsDisallowedError(Exception):
    pass


class FetchError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str | None
    content: bytes | None
    headers: httpx.Headers
    not_modified: bool = False


class PoliteHttpClient:
    """Klientas naudoja vieną per-domeną paskutinės užklausos laiką, kad būtų
    palaikoma minimali pauzė. Naudokite vieną instanciją visam CrawlRun.
    """

    def __init__(
        self,
        user_agent: str,
        allowed_domains: list[str],
        min_delay_seconds: float = 1.5,
        timeout_seconds: float = 20.0,
        max_retries: int = 3,
        max_download_bytes: int = 15 * 1024 * 1024,
        respect_robots: bool = True,
    ) -> None:
        self.user_agent = user_agent
        self.allowed_domains = allowed_domains
        self.min_delay_seconds = min_delay_seconds
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.max_download_bytes = max_download_bytes
        self.respect_robots = respect_robots
        self._last_request_at: dict[str, float] = {}
        self._robots = RobotsCache(user_agent=user_agent, timeout=timeout_seconds)
        self._client = httpx.Client(
            follow_redirects=False,
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "PoliteHttpClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def robots_status(self, url: str) -> str:
        return self._robots.status_for(url)

    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_request_at.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            wait = self.min_delay_seconds - elapsed
            if wait > 0:
                time.sleep(wait)
        self._last_request_at[host] = time.monotonic()

    def get(
        self,
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
        max_redirects: int = 5,
    ) -> FetchResult:
        """GET su SSRF + robots patikra, throttle, retry ir sąlyginėmis antraštėmis."""
        current_url = url
        for _redirect_hop in range(max_redirects + 1):
            check_url_allowed(current_url, self.allowed_domains)
            if self.respect_robots and not self._robots.is_allowed(current_url):
                raise RobotsDisallowedError(f"robots.txt draudžia: {current_url}")

            headers = {}
            if etag:
                headers["If-None-Match"] = etag
            if last_modified:
                headers["If-Modified-Since"] = last_modified

            resp = self._request_with_retry(current_url, headers)

            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("location")
                if not location:
                    raise FetchError("Peradresavimas be Location antraštės", resp.status_code)
                current_url = httpx.URL(current_url).join(location).human_repr()
                continue

            if resp.status_code == 304:
                return FetchResult(
                    url=current_url,
                    status_code=304,
                    text=None,
                    content=None,
                    headers=resp.headers,
                    not_modified=True,
                )

            content_length = resp.headers.get("content-length")
            if content_length and int(content_length) > self.max_download_bytes:
                raise FetchError(
                    f"Turinys per didelis: {content_length} baitų", resp.status_code
                )

            content = resp.content
            if len(content) > self.max_download_bytes:
                raise FetchError(
                    f"Turinys per didelis po atsisiuntimo: {len(content)} baitų",
                    resp.status_code,
                )

            text: str | None = None
            content_type = resp.headers.get("content-type", "")
            if "text" in content_type or "html" in content_type or "json" in content_type or "xml" in content_type:
                text = resp.text

            return FetchResult(
                url=current_url,
                status_code=resp.status_code,
                text=text,
                content=content,
                headers=resp.headers,
            )
        raise FetchError("Per daug peradresavimų")

    def _request_with_retry(self, url: str, headers: dict[str, str]) -> httpx.Response:
        self._throttle(url)
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return self._client.get(url, headers=headers)
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self.max_retries - 1:
                    backoff = min(2**attempt * 1.0, 20.0)
                    logger.warning(
                        "Klaida gaunant %s (bandymas %d/%d): %s. Laukiama %.1fs.",
                        url,
                        attempt + 1,
                        self.max_retries,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
        assert last_exc is not None
        raise FetchError(f"Nepavyko gauti {url} po {self.max_retries} bandymų: {last_exc}")


__all__ = [
    "PoliteHttpClient",
    "FetchResult",
    "FetchError",
    "RobotsDisallowedError",
    "SsrfBlockedError",
]
