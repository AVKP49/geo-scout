from collections.abc import Callable
from typing import Any

import httpx

from app.scans.engines import EngineAnswer, EngineError, gemini, google_aio, perplexity


def request_engine(engine: str, query: str, city: str, settings: dict[str, Any]) -> EngineAnswer:
    config = settings["PRODUCT"]["engines"][engine]
    if engine == "gemini":
        raise EngineError("TERMS_RESTRICTED")
    adapters: dict[
        str,
        tuple[Callable[[str, str, dict[str, Any]], Any], Callable[[dict[str, Any]], EngineAnswer]],
    ] = {
        "google_aio": (google_aio.payload, google_aio.parse),
        "perplexity": (perplexity.payload, perplexity.parse),
        "gemini": (gemini.payload, gemini.parse),
    }
    build_payload, parse_response = adapters[engine]
    headers, auth = {}, None
    if engine == "google_aio":
        if not settings["DATAFORSEO_LOGIN"] or not settings["DATAFORSEO_PASSWORD"]:
            raise EngineError("NOT_CONFIGURED")
        auth = (settings["DATAFORSEO_LOGIN"], settings["DATAFORSEO_PASSWORD"])
    elif engine == "perplexity":
        if not settings["PERPLEXITY_API_KEY"]:
            raise EngineError("NOT_CONFIGURED")
        headers["Authorization"] = "Bearer " + settings["PERPLEXITY_API_KEY"]
    else:
        if not settings["GEMINI_API_KEY"]:
            raise EngineError("NOT_CONFIGURED")
        headers["x-goog-api-key"] = settings["GEMINI_API_KEY"]
    try:
        with httpx.Client(timeout=30, trust_env=False, auth=auth) as client:
            response = client.post(
                config["endpoint"], json=build_payload(query, city, config), headers=headers
            )
        if response.status_code >= 400:
            raise EngineError("HTTP_ERROR", retryable=response.status_code in {429, 502, 503, 504})
        return parse_response(response.json())
    except httpx.TimeoutException as error:
        # Unknown billing after a timeout: do not repeat a potentially charged call.
        raise EngineError("TIMEOUT") from error
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
        raise EngineError("INVALID_RESPONSE") from error
