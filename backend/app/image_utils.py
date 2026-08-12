"""Image validation and normalization before sending to Claude Vision.

Downscaling large images to Claude's recommended max edge (1568px) cuts latency,
token cost and payload size, and `verify()` rejects corrupt uploads early.
"""

import io

from PIL import Image

# Claude Vision resizes anything larger than ~1568px on the long edge anyway,
# so we do it ourselves to shrink the request.
MAX_DIMENSION = 1568
JPEG_QUALITY = 85


def process_image(data: bytes, max_dim: int = MAX_DIMENSION) -> bytes:
    """Validate `data` as an image and return normalized JPEG bytes.

    - Raises ValueError if the bytes are not a decodable image.
    - Flattens transparency onto white, downscales to `max_dim`, re-encodes JPEG.
    """
    # verify() consumes the file object, so validate on one copy...
    try:
        Image.open(io.BytesIO(data)).verify()
    except Exception as exc:  # noqa: BLE001 - any decode failure means invalid input
        raise ValueError("Invalid or corrupt image file") from exc

    # ...then reopen for actual processing.
    img = Image.open(io.BytesIO(data))

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    else:
        img = img.convert("RGB")

    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue()
