import json
import os
import secrets
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def settings() -> dict[str, Any]:
    env = os.getenv("APP_ENV", "development")
    secret = os.getenv("SECRET_KEY")
    database = os.getenv("DATABASE_URL", "sqlite:///geo-scout.db")
    if database.startswith("postgres://"):
        database = database.replace("postgres://", "postgresql+psycopg://", 1)
    elif database.startswith("postgresql://"):
        database = database.replace("postgresql://", "postgresql+psycopg://", 1)
    if env != "development" and (not secret or database.startswith("sqlite:")):
        raise RuntimeError("Staging/production require SECRET_KEY and PostgreSQL DATABASE_URL.")
    return {
        "APP_ENV": env,
        "SECRET_KEY": secret or secrets.token_hex(32),
        "SQLALCHEMY_DATABASE_URI": database,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "RATELIMIT_STORAGE_URI": os.getenv("REDIS_URL", "memory://")
        if env == "development"
        else os.environ["REDIS_URL"],
        "SCAN_ENABLED": os.getenv("SCAN_ENABLED", "false").lower() == "true",
        "PUBLIC_BASE_URL": os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5050").rstrip("/"),
        "SESSION_COOKIE_SECURE": env != "development",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "MAX_CONTENT_LENGTH": 32_768,
        "PRODUCT": json.loads((ROOT / "config/product.json").read_text()),
        "TRUSTED_PROXY_HOPS": int(os.getenv("TRUSTED_PROXY_HOPS", "0")),
        **{
            key: os.getenv(key, "")
            for key in (
                "PERPLEXITY_API_KEY",
                "GEMINI_API_KEY",
                "DATAFORSEO_LOGIN",
                "DATAFORSEO_PASSWORD",
                "TURNSTILE_SITE_KEY",
                "TURNSTILE_SECRET_KEY",
                "POSTMARK_SERVER_TOKEN",
                "EMAIL_FROM",
                "FOUNDER_CALENDAR_URL",
                "SENTRY_DSN",
            )
        },
    }
