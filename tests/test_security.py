import pytest

from app.security import PublicNetworkBackend, SiteError, normalize_url, public_addresses


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost",
        "http://127.0.0.1",
        "http://10.0.0.1",
        "http://169.254.169.254",
        "http://[::1]",
        "https://example.com:8080",
        "file:///tmp/a",
        "https://user:pass@example.com",
    ],
)
def test_private_and_unsafe_urls_rejected(url):
    with pytest.raises(SiteError):
        normalize_url(url)


def test_same_registered_domain_reservation():
    assert normalize_url("https://www.example.com/path")[1] == "example.com"
    assert normalize_url("https://shop.example.com")[1] == "example.com"
    assert normalize_url("https://customer.github.io")[1] == "customer.github.io"


def test_mixed_public_private_dns_rejected(monkeypatch):
    monkeypatch.setattr(
        "socket.getaddrinfo",
        lambda *a, **k: [
            (None, None, None, None, ("8.8.8.8", 443)),
            (None, None, None, None, ("127.0.0.1", 443)),
        ],
    )
    with pytest.raises(SiteError):
        public_addresses("example.com", 443)


def test_socket_connects_to_checked_address(monkeypatch):
    monkeypatch.setattr("app.security.public_addresses", lambda host, port: ["8.8.8.8"])
    captured = []
    monkeypatch.setattr(
        "httpcore.SyncBackend.connect_tcp", lambda self, host, *args: captured.append(host)
    )
    PublicNetworkBackend().connect_tcp("example.com", 443)
    assert captured == ["8.8.8.8"]
