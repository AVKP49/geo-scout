import re
from decimal import Decimal
from typing import Any

from app.scans.engines import EngineAnswer, EngineError, unique_sources


def payload(query: str, city: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "effort": config["effort"],
        "input": f"Location context: {city}.\nQuestion: {query}",
        "tools": [{"type": "web_search"}],
        "max_output_tokens": config["max_output_tokens"],
        "store": False,
    }


def parse(data: dict[str, Any]) -> EngineAnswer:
    cost = data.get("usage", {}).get("cost", {}).get("total_cost")
    measured = Decimal(str(cost)) if cost is not None else None
    if data.get("status") != "completed":
        raise EngineError("INCOMPLETE_RESPONSE", cost_usd=measured)
    texts: list[str] = []
    sources: list[dict[str, Any]] = []
    retrieved: dict[str, dict[str, Any]] = {}
    for item in data.get("output", []):
        if item.get("type") == "search_results":
            for result in item.get("results", []):
                if result.get("id") is not None:
                    retrieved.setdefault(str(result["id"]), result)
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue  # Retrieved search results alone are not citations in the answer.
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                texts.append(content.get("text", ""))
                sources.extend(
                    a for a in content.get("annotations", []) if a.get("type") == "url_citation"
                )
                # The official Agent API examples also use [1][3] markers with
                # empty annotations. Resolve only explicitly referenced IDs.
                for source_id in re.findall(r"\[(\d+)\]", content.get("text", "")):
                    if source_id in retrieved:
                        sources.append(retrieved[source_id])
    if not texts:
        raise EngineError("MALFORMED_RESPONSE", cost_usd=measured)
    return EngineAnswer(
        sources=unique_sources(sources),
        snippet=" ".join(texts)[:500],
        response_ref=data.get("id"),
        cost_usd=measured,
        cost_basis="provider_reported" if measured is not None else "unknown",
        usage={
            "input_tokens": data.get("usage", {}).get("input_tokens"),
            "output_tokens": data.get("usage", {}).get("output_tokens"),
            "model": data.get("model"),
            "effort": data.get("effort"),
        },
    )
