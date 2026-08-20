"""Golden eval dataset: deterministically generated images + expected properties.

Images are drawn at runtime (no binary assets in the repo). Because we draw
them, we know the ground truth — shapes, colors, and any embedded text — and
can score the model's output against it.
"""

import io
from collections.abc import Callable
from dataclasses import dataclass, field

from PIL import Image, ImageDraw


@dataclass
class EvalCase:
    id: str
    draw_fn: Callable[[ImageDraw.ImageDraw], None]
    # Text expected in extracted_text (case-insensitive substring), or None.
    expected_text: str | None = None
    # Keywords expected somewhere in description + tags + object names.
    expected_keywords: list[str] = field(default_factory=list)

    def image_bytes(self) -> bytes:
        img = Image.new("RGB", (480, 320), (245, 245, 245))
        self.draw_fn(ImageDraw.Draw(img))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()


def _red_circle_hello(d: ImageDraw.ImageDraw) -> None:
    d.ellipse([140, 60, 340, 220], fill=(220, 40, 40))
    d.text((180, 250), "HELLO", fill=(20, 20, 20))


def _blue_square_stop(d: ImageDraw.ImageDraw) -> None:
    d.rectangle([150, 70, 330, 230], fill=(40, 70, 210))
    d.text((200, 250), "STOP", fill=(20, 20, 20))


def _green_triangle(d: ImageDraw.ImageDraw) -> None:
    d.polygon([(240, 60), (360, 250), (120, 250)], fill=(40, 170, 70))


def _text_only(d: ImageDraw.ImageDraw) -> None:
    d.text((120, 150), "OPEN 24/7", fill=(10, 10, 10))


def _yellow_circle_red_square(d: ImageDraw.ImageDraw) -> None:
    d.ellipse([60, 100, 200, 240], fill=(240, 210, 40))
    d.rectangle([280, 100, 420, 240], fill=(210, 50, 50))


CASES: list[EvalCase] = [
    EvalCase("red_circle_hello", _red_circle_hello, "hello", ["red", "circle"]),
    EvalCase("blue_square_stop", _blue_square_stop, "stop", ["blue", "square"]),
    EvalCase("green_triangle", _green_triangle, None, ["green", "triangle"]),
    EvalCase("text_only_open", _text_only, "open", ["text"]),
    EvalCase(
        "yellow_circle_red_square",
        _yellow_circle_red_square,
        None,
        ["yellow", "red", "circle", "square"],
    ),
]
