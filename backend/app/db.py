"""SQLite persistence layer for image analyses.

Stores the full analysis payload as JSON alongside a few indexed columns so the
history survives backend restarts. A new connection is opened per call, which is
plenty for this workload and keeps lifecycle management trivial.
"""

import json
from pathlib import Path

import aiosqlite

from app.config import settings

DB_PATH = settings.db_path

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS analyses (
    id          TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    data        TEXT NOT NULL
);
"""


async def init_db() -> None:
    """Create the database file, parent dir and table if needed."""
    parent = Path(DB_PATH).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute(_CREATE_TABLE)
        await db.commit()


async def save_analysis(analysis: dict, file_path: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO analyses "
            "(id, filename, uploaded_at, file_path, data) VALUES (?, ?, ?, ?, ?)",
            (
                analysis["id"],
                analysis["filename"],
                analysis["uploaded_at"],
                file_path,
                json.dumps(analysis),
            ),
        )
        await db.commit()


async def get_all() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT data FROM analyses ORDER BY uploaded_at DESC") as cur:
            rows = await cur.fetchall()
    return [json.loads(row[0]) for row in rows]


async def get_one(image_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT data FROM analyses WHERE id = ?", (image_id,)) as cur:
            row = await cur.fetchone()
    return json.loads(row[0]) if row else None


async def get_file_path(image_id: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT file_path FROM analyses WHERE id = ?", (image_id,)) as cur:
            row = await cur.fetchone()
    return row[0] if row else None


async def get_metrics() -> dict:
    """Aggregate observability metrics across all analyses."""
    query = """
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(json_extract(data, '$.input_tokens')), 0) AS input_tokens,
            COALESCE(SUM(json_extract(data, '$.output_tokens')), 0) AS output_tokens,
            COALESCE(SUM(json_extract(data, '$.cost_usd')), 0) AS cost_usd,
            COALESCE(AVG(json_extract(data, '$.processing_time_ms')), 0) AS avg_ms
        FROM analyses
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(query) as cur:
            row = await cur.fetchone()

    assert row is not None  # the aggregate query always returns one row
    total, input_tokens, output_tokens, cost_usd, avg_ms = row
    return {
        "total_analyses": int(total),
        "total_input_tokens": int(input_tokens),
        "total_output_tokens": int(output_tokens),
        "total_cost_usd": round(float(cost_usd), 6),
        "avg_processing_time_ms": round(float(avg_ms), 1),
    }


async def delete(image_id: str) -> str | None:
    """Delete a row. Returns the stored file_path if it existed, else None."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT file_path FROM analyses WHERE id = ?", (image_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        await db.execute("DELETE FROM analyses WHERE id = ?", (image_id,))
        await db.commit()
    return row[0]
