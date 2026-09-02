"""robots.txt tikrinimas su paprastu atminties cache vienam crawl paleidimui."""

from __future__ import annotations

import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx


@dataclass
class RobotsCache:
    user_agent: str
    timeout: float = 10.0
    _parsers: dict[str, urllib.robotparser.RobotFileParser | None] = field(default_factory=dict)
    _status: dict[str, str] = field(default_factory=dict)

    def _origin(self, url: str) -> str:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"

    def _load(self, origin: str) -> None:
        if origin in self._parsers:
            return
        robots_url = origin + "/robots.txt"
        parser = urllib.robotparser.RobotFileParser()
        try:
            resp = httpx.get(
                robots_url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
            )
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
                self._parsers[origin] = parser
                self._status[origin] = "allowed"
            elif resp.status_code in (401, 403):
                # Serveris blokuoja net robots.txt (dažnai bot-apsaugos iššūkis).
                self._parsers[origin] = None
                self._status[origin] = "unreachable"
            elif resp.status_code == 404:
                # Nėra robots.txt => viskas leidžiama.
                self._parsers[origin] = None
                self._status[origin] = "allowed"
            else:
                self._parsers[origin] = None
                self._status[origin] = "unknown"
        except httpx.HTTPError:
            self._parsers[origin] = None
            self._status[origin] = "unreachable"

    def is_allowed(self, url: str) -> bool:
        origin = self._origin(url)
        self._load(origin)
        parser = self._parsers.get(origin)
        if parser is None:
            # Nepavyko atsisiųsti arba nėra robots.txt: konservatyviai leidžiame,
            # nebent statusas "unreachable" dėl 401/403 (tikėtina bot apsauga) —
            # tokiu atveju atsakomybė perkeliama į SourceCheckResult (blocked_bot_protection),
            # todėl leidžiam kviesti (užklausą vis tiek atmes bot apsauga pati svetainė).
            return True
        return parser.can_fetch(self.user_agent, url)

    def status_for(self, url: str) -> str:
        origin = self._origin(url)
        self._load(origin)
        return self._status.get(origin, "unknown")
