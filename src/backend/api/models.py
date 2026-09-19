"""ORM model for persisted pipeline runs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.api.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    window_end: Mapped[str] = mapped_column(String(64), nullable=False)
    lookback_days: Mapped[int] = mapped_column(nullable=False)
    horizon_hours: Mapped[int] = mapped_column(nullable=False)

    forecast_model: Mapped[str] = mapped_column(String(16), default="seasonal", nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scenario: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    progress_log: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
