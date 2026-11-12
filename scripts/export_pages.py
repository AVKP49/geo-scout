"""Export the public preview and fictional reports for GitHub Pages.

Run from the repository root: .venv/bin/python scripts/export_pages.py
The output contains no database records, credentials or real scan results.
"""

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402


def main() -> None:
    destination = ROOT / "dist" / "pages"
    destination.mkdir(parents=True, exist_ok=True)
    app = create_app(
        {
            "APP_ENV": "development",
            "SECRET_KEY": "static-preview-export-only",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "RATELIMIT_ENABLED": False,
            "SCAN_ENABLED": False,
            "TURNSTILE_SITE_KEY": "",
            "SENTRY_DSN": "",
        }
    )
    app.jinja_env.globals["static_preview"] = True
    paths = ["/", "/sample/hvac", "/sample/plumber", "/sample/food", "/privacy"]
    with app.test_client() as client:
        for path in paths:
            response = client.get(path)
            if response.status_code != 200:
                raise RuntimeError(f"Could not render {path}: {response.status_code}")
            html = response.get_data(as_text=True)
            html = re.sub(r'((?:href|src|action)=")/(?!/)', r"\1/geo-scout/", html)
            output = destination / path.strip("/") / "index.html"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(html)
    shutil.copytree(ROOT / "static", destination / "static", dirs_exist_ok=True)
    product = app.config["PRODUCT"]
    (destination / "static" / "preview-questions.json").write_text(
        json.dumps({key: product[key] for key in ("categories", "default_queries")})
    )
    (destination / ".nojekyll").write_text("")
    (destination / "robots.txt").write_text("User-agent: *\nDisallow: /geo-scout/sample/\n")
    print(f"Exported {len(paths)} preview pages to {destination}")


if __name__ == "__main__":
    main()
