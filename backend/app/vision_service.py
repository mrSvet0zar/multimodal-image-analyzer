import base64
from typing import Any, AsyncIterator, Dict, Tuple

import anthropic

from app.config import settings
from app.cost import usage_to_dict
from app.logging_setup import logger

# Media types Claude Vision accepts.
SUPPORTED_MEDIA_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}

# Description length per detail level (used by both paths).
DETAIL_DESC = {
    "simple": "a brief 1-2 sentence description",
    "medium": "a clear 2-3 sentence description",
    "detailed": "a detailed 4-5 sentence description",
}

# Non-streaming path: a forced tool call guarantees a schema-valid object —
# no fragile JSON scraping from free text.
ANALYSIS_TOOL: Dict[str, Any] = {
    "name": "record_image_analysis",
    "description": "Record the structured visual analysis of the image.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "description": {"type": "string", "description": "Natural-language description."},
            "objects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["name", "confidence"],
                },
            },
            "sentiment": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "extracted_text": {"type": "string"},
        },
        "required": ["description", "objects", "sentiment", "tags", "extracted_text"],
    },
}

# Streaming path: prose description, then this marker, then the JSON tail — lets
# us stream a clean description and parse the structured fields at the end.
STREAM_MARKER = "###DATA###"
STREAM_DESC = DETAIL_DESC


class VisionAnalyzer:
    def __init__(self):
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy backend/.env.example to "
                "backend/.env and add your key."
            )
        client_kwargs = dict(
            api_key=settings.anthropic_api_key,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
        )
        self.client = anthropic.Anthropic(**client_kwargs)
        self.async_client = anthropic.AsyncAnthropic(**client_kwargs)
        self.models = settings.models

    @staticmethod
    def _image_block(image_data: bytes, media_type: str) -> dict:
        if media_type not in SUPPORTED_MEDIA_TYPES:
            media_type = "image/jpeg"
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.standard_b64encode(image_data).decode("utf-8"),
            },
        }

    async def _create_with_fallback(self, **kwargs):
        """Call messages.create, trying the fallback model on overload/5xx/429.

        The SDK already retries retryable errors `max_retries` times per model;
        this adds a cross-model fallback once those are exhausted. Non-retryable
        4xx errors (e.g. bad request) are raised immediately.
        """
        last_exc: Exception | None = None
        for model in self.models:
            try:
                return await self.async_client.messages.create(model=model, **kwargs)
            except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
                status = getattr(exc, "status_code", None)
                if status is not None and 400 <= status < 500 and status != 429:
                    raise
                last_exc = exc
                logger.warning("vision_model_failed", model=model, error=str(exc))
        assert last_exc is not None
        raise last_exc

    async def analyze_image(
        self,
        image_data: bytes,
        media_type: str = "image/jpeg",
        detail_level: str = "medium",
        language: str = "en",
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Analyze an image and return (structured_analysis, usage).

        Uses forced tool use so the analysis always matches the schema.
        """
        desc = DETAIL_DESC.get(detail_level, DETAIL_DESC["medium"])
        instruction = (
            f"Analyze this image and call record_image_analysis with {desc}, "
            "the main objects (each with a confidence between 0 and 1), the overall "
            "sentiment, 5-10 relevant tags, and any text visible in the image "
            "(empty string if none)."
        )
        if language and language != "en":
            instruction += f"\n\nWrite all text values in this language: {language}."

        message = await self._create_with_fallback(
            max_tokens=1500,
            tools=[ANALYSIS_TOOL],
            tool_choice={"type": "tool", "name": ANALYSIS_TOOL["name"]},
            messages=[
                {
                    "role": "user",
                    "content": [
                        self._image_block(image_data, media_type),
                        {"type": "text", "text": instruction},
                    ],
                }
            ],
        )

        data: Dict[str, Any] = {}
        for block in message.content:
            if block.type == "tool_use" and block.name == ANALYSIS_TOOL["name"]:
                data = dict(block.input)
                break

        data.setdefault("description", "")
        data.setdefault("objects", [])
        data.setdefault("sentiment", "neutral")
        data.setdefault("tags", [])
        data.setdefault("extracted_text", "")

        return data, usage_to_dict(message.usage)

    async def stream_analyze_image(
        self,
        image_data: bytes,
        media_type: str = "image/jpeg",
        detail_level: str = "medium",
        language: str = "en",
    ) -> AsyncIterator[Any]:
        """Yield text chunks (prose description, then MARKER + JSON), then a final
        dict `{"__usage__": {...}}` carrying token usage."""
        desc = STREAM_DESC.get(detail_level, STREAM_DESC["medium"])
        prompt = (
            f"Analyze this image. First, write {desc} as plain prose "
            "(no headings, no JSON, no markdown). Then output a line containing "
            f"exactly {STREAM_MARKER} and nothing else, followed by a single JSON "
            'object with keys: objects (array of {"name": string, "confidence": '
            "number between 0 and 1}), sentiment (short string), tags (array of "
            "5-10 strings), extracted_text (string, empty if none)."
        )
        if language and language != "en":
            prompt += (
                f"\n\nWrite the description and all text values in this "
                f"language: {language}."
            )

        async with self.async_client.messages.stream(
            model=self.models[0],
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        self._image_block(image_data, media_type),
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        ) as stream:
            async for text in stream.text_stream:
                yield text
            final = await stream.get_final_message()
            yield {"__usage__": usage_to_dict(final.usage)}

    @classmethod
    def parse_stream_output(cls, full_text: str) -> Dict[str, Any]:
        """Split streamed text into description + structured fields."""
        if STREAM_MARKER in full_text:
            description, _, rest = full_text.partition(STREAM_MARKER)
            data = cls._parse_json(rest)
        else:
            description, data = full_text, {}

        if not isinstance(data, dict):
            data = {}
        data["description"] = description.strip()
        data.setdefault("objects", [])
        data.setdefault("sentiment", "neutral")
        data.setdefault("tags", [])
        data.setdefault("extracted_text", "")
        return data

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        """Extract the first JSON object from text (streaming tail fallback)."""
        import json

        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            try:
                parsed = json.loads(text[json_start:json_end])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        return {"description": text.strip()}
