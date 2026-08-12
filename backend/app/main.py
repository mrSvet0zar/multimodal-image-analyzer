import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.schemas import AnalysisObject, ImageAnalysis
from app.vision_service import SUPPORTED_MEDIA_TYPES, VisionAnalyzer

load_dotenv()

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))

# In-memory stores (swap for a DB in production).
analyzed_images: dict[str, dict] = {}
image_paths: dict[str, Path] = {}

vision_analyzer: VisionAnalyzer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown. Verifies the Claude API connection once on boot."""
    global vision_analyzer
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    try:
        vision_analyzer = VisionAnalyzer()
        vision_analyzer.client.messages.create(
            model=vision_analyzer.model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}],
        )
        print(f"[OK] Claude API connection successful (model: {vision_analyzer.model})")
    except Exception as e:  # noqa: BLE001 - surface any startup failure clearly
        print(f"[WARN] Claude API check failed: {e}")
    yield


app = FastAPI(title="Image Analyzer API", version="1.0.0", lifespan=lifespan)

_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_analyzer() -> VisionAnalyzer:
    if vision_analyzer is None:
        raise HTTPException(status_code=503, detail="Vision service not initialized")
    return vision_analyzer


async def _process_upload(
    content: bytes,
    filename: str,
    content_type: str | None,
    detail_level: str,
    language: str,
) -> ImageAnalysis:
    """Validate, persist and analyze a single image. Shared by both endpoints."""
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE} bytes",
        )

    if content_type not in SUPPORTED_MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format. Supported: JPEG, PNG, GIF, WebP",
        )

    image_id = str(uuid.uuid4())
    extension = filename.rsplit(".", 1)[-1] if "." in filename else "img"
    file_path = UPLOAD_DIR / f"{image_id}.{extension}"

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    image_paths[image_id] = file_path

    start_time = time.time()
    analysis_data = await _get_analyzer().analyze_image(
        content,
        media_type=content_type,
        detail_level=detail_level,
        language=language,
    )
    processing_time = (time.time() - start_time) * 1000

    objects: list[AnalysisObject] = []
    raw_objects = analysis_data.get("objects", [])
    if isinstance(raw_objects, list):
        for obj in raw_objects:
            if isinstance(obj, dict):
                try:
                    confidence = float(obj.get("confidence", 0.8))
                except (TypeError, ValueError):
                    confidence = 0.8
                objects.append(
                    AnalysisObject(
                        name=str(obj.get("name", "")),
                        confidence=max(0.0, min(1.0, confidence)),
                        description=obj.get("description"),
                    )
                )
            elif isinstance(obj, str):
                objects.append(AnalysisObject(name=obj, confidence=0.8))

    result = ImageAnalysis(
        id=image_id,
        filename=filename,
        uploaded_at=datetime.now(timezone.utc),
        description=analysis_data.get("description", ""),
        objects=objects,
        sentiment=str(analysis_data.get("sentiment", "neutral")),
        tags=[str(t) for t in analysis_data.get("tags", []) if t],
        extracted_text=str(analysis_data.get("extracted_text", "")),
        processing_time_ms=processing_time,
        image_url=f"/api/images/{image_id}",
    )

    analyzed_images[image_id] = result.model_dump(mode="json")
    return result


# ============ Image Upload & Analysis ============


@app.post("/api/analyze/image", response_model=ImageAnalysis)
async def analyze_image(
    file: UploadFile = File(...),
    detail_level: str = "medium",
    language: str = "en",
):
    """Upload and analyze a single image."""
    content = await file.read()
    return await _process_upload(
        content, file.filename or "image", file.content_type, detail_level, language
    )


@app.post("/api/analyze/batch")
async def batch_analyze(
    files: list[UploadFile] = File(...),
    detail_level: str = "medium",
    language: str = "en",
):
    """Analyze multiple images in one request."""
    results: list[dict] = []
    for file in files:
        try:
            content = await file.read()
            analysis = await _process_upload(
                content,
                file.filename or "image",
                file.content_type,
                detail_level,
                language,
            )
            results.append(analysis.model_dump(mode="json"))
        except HTTPException as e:
            results.append({"error": e.detail, "filename": file.filename})
        except Exception as e:  # noqa: BLE001
            results.append({"error": str(e), "filename": file.filename})

    return {
        "total": len(files),
        "successful": sum(1 for r in results if "error" not in r),
        "results": results,
    }


# ============ History & Retrieval ============


@app.get("/api/history")
async def get_history():
    """Get analysis history (most recent first)."""
    return sorted(
        analyzed_images.values(),
        key=lambda a: a.get("uploaded_at", ""),
        reverse=True,
    )


@app.get("/api/analysis/{image_id}")
async def get_analysis(image_id: str):
    """Get the analysis metadata for an image."""
    if image_id not in analyzed_images:
        raise HTTPException(status_code=404, detail="Image not found")
    return analyzed_images[image_id]


@app.get("/api/images/{image_id}")
async def get_image_file(image_id: str):
    """Serve the raw uploaded image so the frontend can display it."""
    path = image_paths.get(image_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


# ============ Export ============


@app.get("/api/export/{image_id}")
async def export_analysis(image_id: str, format: str = "json"):
    """Export an analysis as JSON or Markdown."""
    if image_id not in analyzed_images:
        raise HTTPException(status_code=404, detail="Image not found")

    data = analyzed_images[image_id]

    if format == "json":
        return JSONResponse(data)

    if format == "markdown":
        objects_md = "\n".join(
            f"- {obj['name']} (confidence: {obj['confidence']:.0%})"
            for obj in data["objects"]
        ) or "_None detected_"
        tags_md = ", ".join(data["tags"]) or "_None_"
        md = f"""# Analysis: {data['filename']}

## Description
{data['description']}

## Objects Detected
{objects_md}

## Sentiment
{data['sentiment']}

## Tags
{tags_md}

## Extracted Text
{data['extracted_text'] or '_None_'}

---
*Analyzed at: {data['uploaded_at']}*
*Processing time: {data['processing_time_ms']:.0f}ms*
"""
        return JSONResponse({"markdown": md})

    raise HTTPException(status_code=400, detail="Unsupported format")


# ============ Health ============


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", 8000)),
        reload=True,
    )
