from decimal import Decimal
from typing import Any

from app.scans.engines import EngineAnswer, EngineError, unique_sources


def payload(query: str, city: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "keyword": query,
            "location_name": config["location"],
            "language_code": config["language"],
            "device": "desktop",
            "load_async_ai_overview": True,
        }
    ]


def parse(data: dict[str, Any]) -> EngineAnswer:
    cost = data.get("cost")
    measured = Decimal(str(cost)) if cost is not None else None
    tasks = data.get("tasks", [])
    if data.get("status_code") != 20000 or not tasks or tasks[0].get("status_code") != 20000:
        raise EngineError("PROVIDER_TASK_FAILED", cost_usd=measured)
    results = tasks[0].get("result")
    if not isinstance(results, list) or not results:
        raise EngineError("MALFORMED_RESPONSE", cost_usd=measured)
    blocks = [item for item in results[0].get("items", []) if item.get("type") == "ai_overview"]
    sources: list[dict[str, Any]] = []
    texts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "ai_overview_reference":
                sources.append(node)
            if isinstance(node.get("text"), str):
                texts.append(node["text"])
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(blocks)
    return EngineAnswer(
        sources=unique_sources(sources),
        snippet=" ".join(texts)[:500],
        response_ref=tasks[0].get("id"),
        cost_usd=measured,
        cost_basis="provider_reported" if measured is not None else "unknown",
        no_overview=not blocks,
    )
