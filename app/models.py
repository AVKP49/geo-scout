import secrets
from datetime import UTC, datetime
from typing import Any

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def now() -> datetime:
    return datetime.now(UTC)


def identifier() -> str:
    return secrets.token_urlsafe(24)


class FreeScan(Base):
    __tablename__ = "free_scans"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    report_slug: Mapped[str] = mapped_column(String(64), unique=True, default=identifier)
    business_name: Mapped[str] = mapped_column(String(100))
    website_url: Mapped[str] = mapped_column(Text)
    normalized_domain: Mapped[str] = mapped_column(String(255), index=True)
    city: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(40))
    queries: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    site_evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    progress: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_hash: Mapped[str] = mapped_column(String(64))


class DomainReservation(Base):
    __tablename__ = "domain_reservations"
    domain: Mapped[str] = mapped_column(String(255), primary_key=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("free_scans.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ScanResult(Base):
    __tablename__ = "scan_results"
    __table_args__ = (UniqueConstraint("scan_id", "query_index", "engine"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    scan_id: Mapped[str] = mapped_column(ForeignKey("free_scans.id"), index=True)
    query_index: Mapped[int]
    engine: Mapped[str] = mapped_column(String(30))
    state: Mapped[str] = mapped_column(String(30))
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    snippet: Mapped[str] = mapped_column(String(500), default="")
    response_ref: Mapped[str | None] = mapped_column(String(200))
    error_code: Mapped[str | None] = mapped_column(String(50))
    usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    cost_usd: Mapped[Any | None] = mapped_column(Numeric(14, 8))
    cost_basis: Mapped[str] = mapped_column(String(30), default="unknown")
    attempts: Mapped[int] = mapped_column(default=1)


class DemandCache(Base):
    __tablename__ = "demand_cache"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[int | None]
    source: Mapped[str] = mapped_column(String(100))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CostEntry(Base):
    __tablename__ = "scan_costs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    scan_id: Mapped[str] = mapped_column(ForeignKey("free_scans.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    amount_usd: Mapped[Any | None] = mapped_column(Numeric(14, 8))
    basis: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EmailCapture(Base):
    __tablename__ = "email_captures"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    scan_id: Mapped[str] = mapped_column(ForeignKey("free_scans.id"), unique=True)
    email: Mapped[str] = mapped_column(String(254))
    unsubscribe_token: Mapped[str] = mapped_column(String(64), default=identifier, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"
    __table_args__ = (UniqueConstraint("capture_id", "sequence"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    capture_id: Mapped[str] = mapped_column(ForeignKey("email_captures.id"))
    sequence: Mapped[int]
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="attempted")


class Event(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    name: Mapped[str] = mapped_column(String(50), index=True)
    scan_id: Mapped[str | None] = mapped_column(ForeignKey("free_scans.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
