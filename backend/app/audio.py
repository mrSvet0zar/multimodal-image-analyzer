"""Audio transcription via OpenAI Whisper (best-effort, disabled without a key)."""

import asyncio
import io

from app.config import settings
from app.logging_setup import logger


async def transcribe_audio(media_bytes: bytes, filename: str) -> str:
    """Transcribe a media file's audio. Returns '' if disabled or on failure."""
    if not settings.openai_api_key:
        return ""

    def _run() -> str:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        buffer = io.BytesIO(media_bytes)
        buffer.name = filename or "video.mp4"
        result = client.audio.transcriptions.create(model=settings.whisper_model, file=buffer)
        return result.text

    try:
        text = await asyncio.to_thread(_run)
        return text.strip()
    except Exception as exc:  # noqa: BLE001 - transcription is best-effort
        logger.warning("transcription_failed", error=str(exc))
        return ""
