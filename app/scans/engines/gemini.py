from typing import Any

from app.scans.engines import EngineAnswer, EngineError


def payload(query: str, city: str, config: dict[str, Any]) -> dict[str, Any]:
    raise EngineError("TERMS_RESTRICTED")


def parse(data: dict[str, Any]) -> EngineAnswer:
    raise EngineError("TERMS_RESTRICTED")
