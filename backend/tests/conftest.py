import io
import os

# Env must be set before importing the app modules.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ["RATE_LIMIT_MAX"] = "10000"  # don't trip the limiter during API tests

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from PIL import Image

SAMPLE_ANALYSIS = {
    "description": "a test image",
    "objects": [{"name": "square", "confidence": 0.9}],
    "sentiment": "neutral",
    "tags": ["test", "unit"],
    "extracted_text": "hi",
}

SAMPLE_USAGE = {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.00105}


def make_image_bytes(size=(64, 64), color=(120, 80, 200), fmt="PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture
def png_bytes() -> bytes:
    return make_image_bytes()


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the db module at a fresh file for this test."""
    from app import db

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    return db


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with an isolated DB, upload dir, and a mocked vision service."""
    from app import db, main

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(main, "UPLOAD_DIR", uploads)

    asyncio.run(db.init_db())

    mock = AsyncMock()
    mock.analyze_image = AsyncMock(
        return_value=(dict(SAMPLE_ANALYSIS), dict(SAMPLE_USAGE))
    )
    monkeypatch.setattr(main, "vision_analyzer", mock)

    # No context manager -> lifespan doesn't run -> our mock stays in place.
    return TestClient(main.app)
