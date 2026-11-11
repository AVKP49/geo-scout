from pathlib import Path
from typing import Any

from celery import Celery, Task
from flask import Flask, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import ROOT, settings
from app.models import db

limiter = Limiter(key_func=get_remote_address, default_limits=["300 per hour"])
csrf = CSRFProtect()


def create_app(overrides: dict[str, Any] | None = None) -> Flask:
    app = Flask(
        __name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static")
    )
    app.config.update(settings())
    app.config.update(overrides or {})
    Path(app.instance_path).mkdir(exist_ok=True)
    hops = app.config["TRUSTED_PROXY_HOPS"]
    if hops:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops)  # type: ignore[method-assign]
    db.init_app(app)
    Migrate(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    class FlaskTask(Task):  # type: ignore[misc]
        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery = Celery(app.name, task_cls=FlaskTask)
    celery.conf.update(
        broker_url=app.config["REDIS_URL"],
        result_backend=app.config["REDIS_URL"],
        task_ignore_result=True,
        task_serializer="json",
        accept_content=["json"],
        broker_connection_retry_on_startup=True,
        task_soft_time_limit=300,
        task_time_limit=330,
        beat_schedule={"free-scan-emails": {"task": "app.mail.send_due_emails", "schedule": 300}},
    )
    celery.set_default()
    app.extensions["celery"] = celery
    from app import mail  # noqa: F401
    from app.scans import tasks  # noqa: F401
    from app.web.routes import web

    app.register_blueprint(web)
    app.jinja_env.globals.update(product=app.config["PRODUCT"])
    with app.app_context():
        from app.commands import register_commands

        register_commands()
    if app.config["SENTRY_DSN"]:
        import sentry_sdk

        sentry_sdk.init(dsn=app.config["SENTRY_DSN"], send_default_pii=False)

    @app.after_request
    def headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://challenges.cloudflare.com; "
            "style-src 'self'; frame-src https://challenges.cloudflare.com; "
            "connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'"
        )
        if app.config["APP_ENV"] != "development":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    return app
