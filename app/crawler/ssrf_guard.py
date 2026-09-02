"""SSRF apsauga: crawleris gali lankyti tik viešus HTTP(S) domenus, esančius
šaltinio registro leidžiamų domenų sąraše, ir tik viešus IP adresus.

Naudojama prieš KIEKVIENĄ užklausą (pradinę ir po kiekvieno peradresavimo).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class SsrfBlockedError(Exception):
    pass


_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "data", "javascript"}


def _is_public_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
        return False
    if ip.is_unspecified:
        return False
    return True


def domain_matches(host: str, allowed: str) -> bool:
    host = host.lower().rstrip(".")
    allowed = allowed.lower().lstrip("*.").rstrip(".")
    return host == allowed or host.endswith("." + allowed)


def check_url_allowed(url: str, allowed_domains: list[str]) -> None:
    """Meta SsrfBlockedError, jei URL neatitinka saugumo taisyklių."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise SsrfBlockedError(f"Neleidžiama schema: {parsed.scheme!r}")

    host = parsed.hostname
    if not host:
        raise SsrfBlockedError("URL neturi host dalies")

    if host in ("localhost",) or host.endswith(".localhost"):
        raise SsrfBlockedError(f"Blokuojamas localhost: {host}")

    if not any(domain_matches(host, d) for d in allowed_domains):
        raise SsrfBlockedError(f"Domenas {host!r} nėra leidžiamų domenų sąraše")

    # Patikriname, kad host neišsprendžia į privatų/loopback IP (DNS rebinding apsauga).
    try:
        # Jei host jau yra IP literalas.
        ipaddress.ip_address(host)
        addrs = [host]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
            addrs = {info[4][0] for info in infos}
        except OSError as exc:
            raise SsrfBlockedError(f"Nepavyko išspręsti host {host!r}: {exc}") from exc

    for addr in addrs:
        if not _is_public_ip(addr):
            raise SsrfBlockedError(f"Host {host!r} nurodo į neviešą IP {addr!r}")
