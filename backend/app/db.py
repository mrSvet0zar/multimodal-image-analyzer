"""SQLite persistence layer for image analyses.

Stores the full analysis payload as JSON alongside a few indexed columns so the
history survives backend restarts. A new connection is opened per call, which is
plenty for this workload and keeps lifecycle management trivial.
"""

import json
import os
from pathlib import Path

import aiosqlite

DB_PATH = os.getenv("DB_PATH", "./analyses.db")

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
        async with db.execute(
            "SELECT data FROM analyses ORDER BY uploaded_at DESC"
        ) as cur:
            rows = await cur.fetchall()
    return [json.loads(row[0]) for row in rows]


async def get_one(image_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT data FROM analyses WHERE id = ?", (image_id,)
        ) as cur:
            row = await cur.fetchone()
    return json.loads(row[0]) if row else None


async def get_file_path(image_id: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT file_path FROM analyses WHERE id = ?", (image_id,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else None


async def delete(image_id: str) -> str | None:
    """Delete a row. Returns the stored file_path if it existed, else None."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT file_path FROM analyses WHERE id = ?", (image_id,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        await db.execute("DELETE FROM analyses WHERE id = ?", (image_id,))
        await db.commit()
    return row[0]
