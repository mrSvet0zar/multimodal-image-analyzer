"""Extract evenly-spaced frames from a video for multi-image analysis.

Uses OpenCV (headless) to decode the video, samples `count` frames across its
duration, and returns them as resized JPEGs plus a thumbnail (middle frame).
"""

import io
import os
import tempfile

import cv2
from PIL import Image

MAX_FRAME_DIM = 1024  # keep per-frame payload/token cost reasonable
JPEG_QUALITY = 85


def _encode_frame(frame_bgr) -> bytes:
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb)
    if max(img.size) > MAX_FRAME_DIM:
        img.thumbnail((MAX_FRAME_DIM, MAX_FRAME_DIM), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue()


def extract_frames(video_bytes: bytes, count: int) -> tuple[list[bytes], bytes]:
    """Return (frame_jpegs, thumbnail_jpeg). Raises ValueError on a bad video."""
    with tempfile.NamedTemporaryFile(suffix=".video", delete=False) as tmp:
        tmp.write(video_bytes)
        path = tmp.name

    try:
        capture = cv2.VideoCapture(path)
        if not capture.isOpened():
            raise ValueError("Invalid or unreadable video file")

        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        frames: list[bytes] = []

        if total > 0:
            n = max(1, min(count, total))
            if n == 1:
                indices = [0]
            else:
                indices = [round(i * (total - 1) / (n - 1)) for i in range(n)]
            for idx in indices:
                capture.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = capture.read()
                if ok:
                    frames.append(_encode_frame(frame))
        else:
            # Frame count unknown: read sequentially and sample.
            all_frames: list = []
            ok, frame = capture.read()
            while ok and len(all_frames) < 2000:
                all_frames.append(frame)
                ok, frame = capture.read()
            if all_frames:
                step = max(1, len(all_frames) // count)
                frames = [_encode_frame(f) for f in all_frames[::step][:count]]

        capture.release()

        if not frames:
            raise ValueError("Could not extract frames from video")

        thumbnail = frames[len(frames) // 2]
        return frames, thumbnail
    finally:
        os.unlink(path)
