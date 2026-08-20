"""Async persistence layer (SQLAlchemy 2.0).

Speaks SQLite (dev/tests) or Postgres (prod) via a single code path — the driver
is selected by `DATABASE_URL`. Public functions keep dict in / dict out so the
rest of the app is storage-agnostic.
"""

from typing import Any

from sqlalchemy import JSON, Float, Integer, String, Text, func, select
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    pass


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    uploaded_at: Mapped[str] = mapped_column(String(64), index=True)
    file_path: Mapped[str] = mapped_column(String(1024))
    description: Mapped[str] = mapped_column(Text, default="")
    sentiment: Mapped[str] = mapped_column(String(128), default="neutral")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    objects: Mapped[list] = mapped_column(JSON, default=list)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "uploaded_at": self.uploaded_at,
            "description": self.description,
            "objects": self.objects or [],
            "sentiment": self.sentiment,
            "tags": self.tags or [],
            "extracted_text": self.extracted_text,
            "processing_time_ms": self.processing_time_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "image_url": f"/api/images/{self.id}",
        }


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker | None = None


def configure(database_url: str | None = None) -> None:
    """(Re)create the engine + session factory. Called at import and by tests."""
    global _engine, _sessionmaker
    url = database_url or settings.async_database_url
    kwargs: dict[str, Any] = {}
    if url.startswith("sqlite"):
        # Avoid binding pooled connections to a specific event loop (tests).
        kwargs["poolclass"] = NullPool
    _engine = create_async_engine(url, **kwargs)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)


configure()


async def init_db() -> None:
    """Create tables if missing. Dev/test convenience; prod uses Alembic."""
    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_analysis(analysis: dict, file_path: str) -> None:
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        row = Analysis(
            id=analysis["id"],
            filename=analysis["filename"],
            uploaded_at=analysis["uploaded_at"],
            file_path=file_path,
            description=analysis.get("description", ""),
            sentiment=analysis.get("sentiment", "neutral"),
            tags=analysis.get("tags", []),
            objects=analysis.get("objects", []),
            extracted_text=analysis.get("extracted_text", ""),
            processing_time_ms=analysis.get("processing_time_ms", 0.0),
            input_tokens=analysis.get("input_tokens", 0),
            output_tokens=analysis.get("output_tokens", 0),
            cost_usd=analysis.get("cost_usd", 0.0),
        )
        await session.merge(row)
        await session.commit()


async def get_all() -> list[dict]:
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        result = await session.execute(select(Analysis).order_by(Analysis.uploaded_at.desc()))
        return [row.to_dict() for row in result.scalars()]


async def get_one(image_id: str) -> dict | None:
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        row = await session.get(Analysis, image_id)
        return row.to_dict() if row else None


async def get_file_path(image_id: str) -> str | None:
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        row = await session.get(Analysis, image_id)
        return row.file_path if row else None


async def get_metrics() -> dict:
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        result = await session.execute(
            select(
                func.count(Analysis.id),
                func.coalesce(func.sum(Analysis.input_tokens), 0),
                func.coalesce(func.sum(Analysis.output_tokens), 0),
                func.coalesce(func.sum(Analysis.cost_usd), 0.0),
                func.coalesce(func.avg(Analysis.processing_time_ms), 0.0),
            )
        )
        total, input_tokens, output_tokens, cost_usd, avg_ms = result.one()

    return {
        "total_analyses": int(total),
        "total_input_tokens": int(input_tokens),
        "total_output_tokens": int(output_tokens),
        "total_cost_usd": round(float(cost_usd), 6),
        "avg_processing_time_ms": round(float(avg_ms), 1),
    }


async def get_daily_metrics(limit_days: int = 14) -> list[dict]:
    """Per-day analysis count and cost (most recent `limit_days`, chronological)."""
    assert _sessionmaker is not None
    day = func.substr(Analysis.uploaded_at, 1, 10)
    async with _sessionmaker() as session:
        result = await session.execute(
            select(
                day.label("day"),
                func.count(Analysis.id),
                func.coalesce(func.sum(Analysis.cost_usd), 0.0),
            )
            .group_by(day)
            .order_by(day.desc())
            .limit(limit_days)
        )
        rows = result.all()

    return [
        {"day": r[0], "count": int(r[1]), "cost_usd": round(float(r[2]), 6)} for r in reversed(rows)
    ]


async def delete(image_id: str) -> str | None:
    """Delete a row. Returns the stored file_path if it existed, else None."""
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        row = await session.get(Analysis, image_id)
        if row is None:
            return None
        file_path = row.file_path
        await session.execute(sa_delete(Analysis).where(Analysis.id == image_id))
        await session.commit()
        return file_path
