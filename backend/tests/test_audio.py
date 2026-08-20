"""Audio transcription tests (no real OpenAI calls)."""

from app.audio import transcribe_audio


async def test_transcribe_disabled_without_key():
    # OPENAI_API_KEY is unset in tests -> transcription is a no-op.
    assert await transcribe_audio(b"not-real-audio", "clip.mp4") == ""
