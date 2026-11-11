import hashlib
from datetime import timedelta
from decimal import Decimal
from typing import Any

import httpx
from flask import current_app
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models import CostEntry, DemandCache, db, now


def lookup(scan_id: str, queries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    config = current_app.config
    location = config["PRODUCT"]["engines"]["google_aio"]["location"]
    keys = {
        q["text"]: hashlib.sha256(f"{location}|{q['text'].casefold()}".encode()).hexdigest()
        for q in queries
    }
    missing: list[str] = []
    values: dict[str, int | None] = {}
    for text, key in keys.items():
        cached = db.session.get(DemandCache, key)
        if cached and cached.fetched_at.replace(tzinfo=now().tzinfo) > now() - timedelta(days=30):
            values[text] = cached.value
        else:
            missing.append(text)
    if missing and config["DATAFORSEO_LOGIN"] and config["DATAFORSEO_PASSWORD"]:
        try:
            response = httpx.post(
                config["PRODUCT"]["demand_endpoint"],
                auth=(config["DATAFORSEO_LOGIN"], config["DATAFORSEO_PASSWORD"]),
                json=[{"keywords": missing, "location_name": location, "language_code": "en"}],
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            cost = Decimal(str(data["cost"])) if data.get("cost") is not None else None
            db.session.add(
                CostEntry(
                    scan_id=scan_id,
                    provider="DataForSEO keyword volume",
                    amount_usd=cost,
                    basis="provider_reported" if cost is not None else "unknown",
                )
            )
            tasks = data.get("tasks", [])
            if data.get("status_code") == 20000 and tasks and tasks[0].get("status_code") == 20000:
                by_keyword = {
                    row["keyword"].casefold(): row.get("search_volume")
                    for row in (tasks[0].get("result") or [])
                }
                for text in missing:
                    value = by_keyword.get(text.casefold())
                    if value is not None and (not isinstance(value, int) or value < 0):
                        value = None
                    values[text] = value
                    insert = pg_insert if db.engine.dialect.name == "postgresql" else sqlite_insert
                    db.session.execute(
                        insert(DemandCache)
                        .values(
                            key=keys[text],
                            value=value,
                            source=f"DataForSEO Google Ads; {location}",
                            fetched_at=now(),
                        )
                        .on_conflict_do_update(
                            index_elements=["key"], set_={"value": value, "fetched_at": now()}
                        )
                    )
        except (httpx.HTTPError, ValueError, KeyError):
            db.session.add(
                CostEntry(
                    scan_id=scan_id,
                    provider="DataForSEO keyword volume",
                    amount_usd=None,
                    basis="unknown",
                )
            )
    db.session.commit()
    return [
        {
            **q,
            "demand": values.get(q["text"]),
            "demand_source": f"DataForSEO Google Ads; {location}; traditional search estimate",
        }
        for q in queries
    ]
