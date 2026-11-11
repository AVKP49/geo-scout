from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit


@dataclass
class EngineAnswer:
    sources: list[dict[str, Any]] = field(default_factory=list)
    snippet: str = ""
    response_ref: str | None = None
    cost_usd: Decimal | None = None
    cost_basis: str = "unknown"
    usage: dict[str, Any] = field(default_factory=dict)
    no_overview: bool = False


class EngineError(RuntimeError):
    def __init__(self, code: str, retryable: bool = False, cost_usd: Decimal | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.cost_usd = cost_usd


def unique_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    clean = []
    for source in sources:
        url = source.get("url", "")
        if not isinstance(url, str) or urlsplit(url).scheme not in {"http", "https"} or url in seen:
            continue
        seen.add(url)
        clean.append({"url": url[:2048], "title": str(source.get("title", ""))[:200]})
    return clean
