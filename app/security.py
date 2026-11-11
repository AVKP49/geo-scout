import hashlib
import hmac
import ipaddress
import socket
import time
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpcore
import httpx
import tldextract
from bs4 import BeautifulSoup
from flask import current_app

extract_domain = tldextract.TLDExtract(suffix_list_urls=(), include_psl_private_domains=True)


class SiteError(ValueError):
    pass


def normalize_url(value: str) -> tuple[str, str]:
    if len(value) > 2048:
        raise SiteError("Website URL is too long.")
    value = value.strip()
    if "://" not in value:
        value = "https://" + value
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise SiteError("Check the website URL.") from error
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or port not in {None, 80, 443}
    ):
        raise SiteError("Use a public HTTP or HTTPS website without a login or custom port.")
    host = parsed.hostname.encode("idna").decode().lower().rstrip(".")
    if host == "localhost" or host.endswith((".local", ".internal")):
        raise SiteError("Use a public website.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not ip.is_global:
            raise SiteError("Use a public website.")
    domain = extract_domain(host).top_domain_under_public_suffix
    if not domain:
        raise SiteError("Use a valid public website domain.")
    netloc = host + (f":{port}" if port else "")
    return urlunsplit((parsed.scheme, netloc, parsed.path or "/", parsed.query, "")), domain


def public_addresses(host: str, port: int) -> list[str]:
    try:
        addresses = list(
            dict.fromkeys(
                str(row[4][0]) for row in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            )
        )
    except OSError as error:
        raise SiteError("We couldn't resolve that website. Check the URL.") from error
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise SiteError("The website must resolve only to public addresses.")
    return addresses


class PublicNetworkBackend(httpcore.SyncBackend):
    """Pin the actual socket to the checked IP; httpcore retains hostname TLS verification."""

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Any = None,
    ) -> Any:
        address = public_addresses(host, port)[0]
        return super().connect_tcp(address, port, timeout, local_address, socket_options)


def fetch_page(url: str) -> dict[str, Any]:
    url, _ = normalize_url(url)
    transport = httpx.HTTPTransport(retries=0)
    transport._pool._network_backend = PublicNetworkBackend()
    deadline = time.monotonic() + 10
    with httpx.Client(
        transport=transport,
        timeout=10,
        trust_env=False,
        headers={"User-Agent": "GEOScout/0.1 (+website visibility check)"},
    ) as client:
        for _ in range(4):
            url, _ = normalize_url(url)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SiteError("We couldn't load that site within 10 seconds. Check the URL.")
            try:
                with client.stream("GET", url, timeout=remaining) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers.get("location", ""))
                        continue
                    if response.status_code != 200:
                        raise SiteError(
                            f"That page returned HTTP {response.status_code}. Check the URL."
                        )
                    if "text/html" not in response.headers.get("content-type", ""):
                        raise SiteError("Use a website page rather than a file.")
                    chunks = bytearray()
                    for chunk in response.iter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > 1_000_000 or time.monotonic() > deadline:
                            raise SiteError("The page is too large or took too long to check.")
            except (httpx.HTTPError, OSError) as error:
                raise SiteError(
                    "We couldn't load that site. Check the URL or try later."
                ) from error
            soup = BeautifulSoup(bytes(chunks), "html.parser")
            schema = bool(soup.find("script", attrs={"type": "application/ld+json"}))
            links = [urljoin(url, str(a["href"])) for a in soup.find_all("a", href=True)]
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            return {
                "url": url,
                "status": 200,
                "text": soup.get_text(" ", strip=True)[:30_000],
                "schema": schema,
                "links": links[:100],
            }
    raise SiteError("That website redirected too many times.")


def ip_hash(ip: str) -> str:
    return hmac.new(current_app.secret_key.encode(), ip.encode(), hashlib.sha256).hexdigest()  # type: ignore[union-attr]


def verify_captcha(token: str, ip: str) -> bool:
    if not token or not current_app.config["TURNSTILE_SECRET_KEY"]:
        return False
    try:
        response = httpx.post(
            current_app.config["PRODUCT"]["turnstile_endpoint"],
            data={
                "secret": current_app.config["TURNSTILE_SECRET_KEY"],
                "response": token,
                "remoteip": ip,
            },
            timeout=10,
        )
        data = response.json()
        expected = urlsplit(current_app.config["PUBLIC_BASE_URL"]).hostname
        return bool(
            data.get("success")
            and data.get("hostname") == expected
            and data.get("action") == "free_scan"
        )
    except (httpx.HTTPError, ValueError):
        return False
