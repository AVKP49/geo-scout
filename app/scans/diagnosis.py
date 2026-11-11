import re
from typing import Any


def recommend(
    query: str, city: str, pages: list[dict[str, Any]], rules: dict[str, Any]
) -> dict[str, Any]:
    successful = [p for p in pages if p.get("status") == 200]
    if not successful:
        key = "retrieval"
        evidence = "None of the attempted pages could be fetched. This does not establish an indexing problem."
    elif not any(
        city.split(",")[0].strip().lower() in p.get("text", "").lower() for p in successful
    ):
        key = "service_area"
        evidence = f'We did not find "{city.split(",")[0].strip()}" in the {len(successful)} pages checked. Other pages may contain it.'
    elif not successful[0].get("schema"):
        key = "schema"
        evidence = (
            f"No JSON-LD detected on {successful[0]['url']}. Other markup formats were not checked."
        )
    else:
        key = "review_content"
        evidence = f"Review suggested from a limited check of {len(successful)} pages; we have not established why the engine selected its sources."
    words = re.sub(r"[^\w\s?,-]", "", query)[:200]
    return {
        **rules[key],
        "kind": key,
        "evidence": evidence,
        "draft": f"Suggested heading: {words}\n\nAnswer with your verified services, the area you actually serve, and a clear next step for customers. Keep the answer useful and specific. Do not invent reviews, prices, qualifications or availability.",
        "pages": [{"url": p["url"], "status": p.get("status")} for p in pages],
    }
