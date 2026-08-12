import io

import pytest
from PIL import Image

from app.image_utils import process_image
from tests.conftest import make_image_bytes


def test_process_image_returns_jpeg():
    result = process_image(make_image_bytes())
    img = Image.open(io.BytesIO(result))
    assert img.format == "JPEG"


def test_process_image_downscales_large_image():
    big = make_image_bytes(size=(4000, 2000))
    result = process_image(big, max_dim=1568)
    img = Image.open(io.BytesIO(result))
    assert max(img.size) <= 1568
    # aspect ratio preserved (2:1)
    assert img.size[0] == 1568 and img.size[1] == 784


def test_process_image_keeps_small_image_dimensions():
    result = process_image(make_image_bytes(size=(100, 100)))
    img = Image.open(io.BytesIO(result))
    assert img.size == (100, 100)


def test_process_image_flattens_transparency():
    buf = io.BytesIO()
    Image.new("RGBA", (50, 50), (255, 0, 0, 0)).save(buf, format="PNG")
    result = process_image(buf.getvalue())
    img = Image.open(io.BytesIO(result))
    assert img.mode == "RGB"


def test_process_image_rejects_invalid_bytes():
    with pytest.raises(ValueError):
        process_image(b"this is not an image")


def test_process_image_rejects_empty_bytes():
    with pytest.raises(ValueError):
        process_image(b"")
