"""Async tests for the SQLite persistence layer (asyncio_mode=auto)."""

SAMPLE = {
    "id": "abc123",
    "filename": "x.png",
    "uploaded_at": "2026-08-12T20:00:00Z",
    "description": "d",
    "objects": [],
    "sentiment": "neutral",
    "tags": ["a", "b"],
    "extracted_text": "",
    "processing_time_ms": 1.0,
    "image_url": "/api/images/abc123",
}


async def test_save_and_get_one(temp_db):
    await temp_db.init_db()
    await temp_db.save_analysis(SAMPLE, "./uploads/abc123.png")

    one = await temp_db.get_one("abc123")
    assert one is not None
    assert one["id"] == "abc123"
    assert one["tags"] == ["a", "b"]


async def test_get_one_missing_returns_none(temp_db):
    await temp_db.init_db()
    assert await temp_db.get_one("nope") is None


async def test_get_all_orders_recent_first(temp_db):
    await temp_db.init_db()
    await temp_db.save_analysis(
        {**SAMPLE, "id": "old", "uploaded_at": "2026-01-01T00:00:00Z"}, "p1"
    )
    await temp_db.save_analysis(
        {**SAMPLE, "id": "new", "uploaded_at": "2026-08-01T00:00:00Z"}, "p2"
    )
    rows = await temp_db.get_all()
    assert [r["id"] for r in rows] == ["new", "old"]


async def test_delete_returns_path_and_removes(temp_db):
    await temp_db.init_db()
    await temp_db.save_analysis(SAMPLE, "./uploads/abc123.png")

    path = await temp_db.delete("abc123")
    assert path == "./uploads/abc123.png"
    assert await temp_db.get_one("abc123") is None


async def test_delete_missing_returns_none(temp_db):
    await temp_db.init_db()
    assert await temp_db.delete("nope") is None
