import anthropic
import base64
import json
import os
from typing import Any, Dict

# Media types Claude Vision accepts, mapped from what the frontend may send.
SUPPORTED_MEDIA_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}

DETAIL_PROMPTS = {
    "simple": (
        "Analyze this image. Return ONLY a JSON object with keys: "
        '"description" (a brief 1-2 sentence description), "objects" '
        '(array of {name, confidence}), "sentiment", "tags" (array of strings), '
        '"extracted_text". Keep it concise.'
    ),
    "medium": (
        "Analyze this image and return ONLY a JSON object with these keys:\n"
        '- "description": a clear 2-3 sentence description\n'
        '- "objects": array of {"name": string, "confidence": number 0-1}\n'
        '- "sentiment": overall mood/sentiment as a single word or short phrase\n'
        '- "tags": array of 5-10 relevant keywords\n'
        '- "extracted_text": any text visible in the image (empty string if none)'
    ),
    "detailed": (
        "Provide a comprehensive analysis of this image. Return ONLY a JSON object "
        "with these keys:\n"
        '- "description": detailed 3-4 sentence description\n'
        '- "objects": array of {"name": string, "confidence": number 0-1, "description": string}\n'
        '- "scene_analysis": {"lighting": string, "composition": string, "style": string}\n'
        '- "sentiment": emotional/sentiment analysis\n'
        '- "colors": array of dominant colors as strings\n'
        '- "use_cases": array of potential use cases\n'
        '- "extracted_text": any text visible in the image (empty string if none)\n'
        '- "quality_score": a number from 0 to 1 assessing image quality'
    ),
}


# Streaming format: prose description, then this marker, then a JSON object with
# the structured fields. Lets us stream a clean description and parse the rest.
STREAM_MARKER = "###DATA###"
STREAM_DESC = {
    "simple": "a brief 1-2 sentence description",
    "medium": "a clear 2-3 sentence description",
    "detailed": "a detailed 4-5 sentence description",
}


class VisionAnalyzer:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy backend/.env.example to "
                "backend/.env and add your key."
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = os.getenv("VISION_MODEL", "claude-sonnet-5")

    async def analyze_image(
        self,
        image_data: bytes,
        media_type: str = "image/jpeg",
        detail_level: str = "medium",
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Analyze an image with Claude Vision and return a structured dict with:
        description, objects, sentiment, tags, extracted_text (plus extra keys
        for the "detailed" level).
        """
        base64_image = base64.standard_b64encode(image_data).decode("utf-8")

        if media_type not in SUPPORTED_MEDIA_TYPES:
            media_type = "image/jpeg"

        prompt = DETAIL_PROMPTS.get(detail_level, DETAIL_PROMPTS["medium"])
        if language and language != "en":
            prompt += f"\n\nWrite all text values in the response in this language: {language}."

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        response_text = message.content[0].text
        analysis = self._parse_json(response_text)

        # Guarantee the fields the API contract depends on.
        analysis.setdefault("description", response_text.strip())
        analysis.setdefault("objects", [])
        analysis.setdefault("sentiment", "neutral")
        analysis.setdefault("tags", [])
        analysis.setdefault("extracted_text", "")

        return analysis

    async def stream_analyze_image(
        self,
        image_data: bytes,
        media_type: str = "image/jpeg",
        detail_level: str = "medium",
        language: str = "en",
    ):
        """Yield text chunks from Claude: prose description, then MARKER + JSON."""
        base64_image = base64.standard_b64encode(image_data).decode("utf-8")
        if media_type not in SUPPORTED_MEDIA_TYPES:
            media_type = "image/jpeg"

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
            model=self.model,
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        ) as stream:
            async for text in stream.text_stream:
                yield text

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
        """Extract the first JSON object from the model's response text."""
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
