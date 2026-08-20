import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import anthropic
import structlog
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse

from app import db
from app.config import settings
from app.cost_guard import CostGuard, InMemoryCostGuard, RedisCostGuard
from app.image_utils import process_image
from app.logging_setup import configure_logging, logger
from app.rate_limit import InMemoryLimiter, Limiter, RedisLimiter, client_key
from app.redis_client import get_redis
from app.schemas import AnalysisObject, ImageAnalysis
from app.storage import get_storage
from app.vision_service import (
    STREAM_MARKER,
    SUPPORTED_MEDIA_TYPES,
    VisionAnalyzer,
)

MAX_FILE_SIZE = settings.max_file_size

vision_analyzer: VisionAnalyzer | None = None
storage = get_storage()

_redis = get_redis()
analyze_limiter: Limiter = (
    RedisLimiter(_redis, settings.rate_limit_max, settings.rate_limit_window)
    if _redis is not None
    else InMemoryLimiter(settings.rate_limit_max, settings.rate_limit_window)
)
cost_guard: CostGuard = (
    RedisCostGuard(_redis, settings.daily_cost_limit_usd)
    if _redis is not None
    else InMemoryCostGuard(settings.daily_cost_limit_usd)
)


async def rate_limit(request: Request) -> None:
    await analyze_limiter.check(client_key(request))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown. Init logging + DB and verify the Claude connection."""
    global vision_analyzer
    configure_logging()
    await db.init_db()
    try:
        vision_analyzer = VisionAnalyzer()
        await vision_analyzer.async_client.messages.create(
            model=settings.vision_model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}],
        )
        logger.info("startup_api_check_ok", model=settings.vision_model)
    except Exception as e:  # noqa: BLE001 - surface any startup failure clearly
        logger.warning("startup_api_check_failed", error=str(e))
    yield


app = FastAPI(title="Image Analyzer API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Attach a request id, bind it to logs, and emit an access log line."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration_ms, 1),
    )
    response.headers["X-Request-ID"] = request_id
    return response


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
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

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

    # Validate + normalize (resize/re-encode) off the event loop.
    try:
        api_bytes = await asyncio.to_thread(process_image, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await cost_guard.check()

    image_id = str(uuid.uuid4())
    extension = filename.rsplit(".", 1)[-1] if "." in filename else "img"

    # Store the original bytes for display; send the normalized JPEG to Claude.
    location = await storage.save(
        f"{image_id}.{extension}", content, content_type or "application/octet-stream"
    )

    start_time = time.time()
    try:
        analysis_data, usage = await _get_analyzer().analyze_image(
            api_bytes,
            media_type="image/jpeg",
            detail_level=detail_level,
            language=language,
        )
    except anthropic.APIError as exc:
        await storage.delete(location)
        logger.error("vision_api_error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Vision service error: {exc}") from exc
    processing_time = (time.time() - start_time) * 1000

    result = _build_result(image_id, filename, analysis_data, processing_time, usage)
    await db.save_analysis(result.model_dump(mode="json"), location)
    await cost_guard.add(usage["cost_usd"])

    logger.info(
        "image_analyzed",
        image_id=image_id,
        model=settings.vision_model,
        detail_level=detail_level,
        language=language,
        streaming=False,
        duration_ms=round(processing_time, 1),
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cost_usd=usage["cost_usd"],
    )
    return result


def _parse_objects(analysis_data: dict) -> list[AnalysisObject]:
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
    return objects


def _build_result(
    image_id: str,
    filename: str,
    analysis_data: dict,
    processing_time: float,
    usage: dict | None = None,
) -> ImageAnalysis:
    usage = usage or {}
    return ImageAnalysis(
        id=image_id,
        filename=filename,
        uploaded_at=datetime.now(timezone.utc),
        description=analysis_data.get("description", ""),
        objects=_parse_objects(analysis_data),
        sentiment=str(analysis_data.get("sentiment", "neutral")),
        tags=[str(t) for t in analysis_data.get("tags", []) if t],
        extracted_text=str(analysis_data.get("extracted_text", "")),
        processing_time_ms=processing_time,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        cost_usd=float(usage.get("cost_usd", 0.0)),
        image_url=f"/api/images/{image_id}",
    )


# ============ Image Upload & Analysis ============


@app.post(
    "/api/analyze/image",
    response_model=ImageAnalysis,
    dependencies=[Depends(rate_limit)],
)
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


@app.post("/api/analyze/batch", dependencies=[Depends(rate_limit)])
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


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@app.post("/api/analyze/stream", dependencies=[Depends(rate_limit)])
async def analyze_stream(
    file: UploadFile = File(...),
    detail_level: str = "medium",
    language: str = "en",
):
    """Analyze a single image, streaming the description as Server-Sent Events.

    Emits `start`, many `delta` (description prose), then `complete` (the full
    persisted analysis) — or `error`. Validation happens before the stream opens
    so bad input still returns a normal 4xx.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, detail=f"File too large. Max size: {MAX_FILE_SIZE} bytes"
        )
    if file.content_type not in SUPPORTED_MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format. Supported: JPEG, PNG, GIF, WebP",
        )
    try:
        api_bytes = await asyncio.to_thread(process_image, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await cost_guard.check()

    analyzer = _get_analyzer()
    filename = file.filename or "image"
    image_id = str(uuid.uuid4())
    extension = filename.rsplit(".", 1)[-1] if "." in filename else "img"

    location = await storage.save(
        f"{image_id}.{extension}",
        content,
        file.content_type or "application/octet-stream",
    )

    async def event_stream():
        start_time = time.time()
        yield _sse(
            {
                "type": "start",
                "id": image_id,
                "filename": filename,
                "image_url": f"/api/images/{image_id}",
            }
        )

        full = ""
        sent = 0  # length of description already streamed
        cut = False  # marker reached — stop streaming, JSON follows
        usage: dict = {}
        try:
            async for chunk in analyzer.stream_analyze_image(
                api_bytes,
                media_type="image/jpeg",
                detail_level=detail_level,
                language=language,
            ):
                # The generator yields a final dict carrying token usage.
                if isinstance(chunk, dict):
                    usage = chunk.get("__usage__", {})
                    continue
                full += chunk
                if cut:
                    continue
                idx = full.find(STREAM_MARKER)
                if idx != -1:
                    description = full[:idx]
                    if len(description) > sent:
                        yield _sse({"type": "delta", "text": description[sent:]})
                    sent = len(description)
                    cut = True
                else:
                    # Hold back a possible partial marker at the tail.
                    emit_upto = len(full) - (len(STREAM_MARKER) - 1)
                    if emit_upto > sent:
                        yield _sse({"type": "delta", "text": full[sent:emit_upto]})
                        sent = emit_upto
        except anthropic.APIError as exc:
            await storage.delete(location)
            logger.error("vision_api_error", error=str(exc), streaming=True)
            yield _sse({"type": "error", "detail": f"Vision service error: {exc}"})
            return

        if not cut and len(full) > sent:
            yield _sse({"type": "delta", "text": full[sent:]})

        processing_time = (time.time() - start_time) * 1000
        analysis_data = VisionAnalyzer.parse_stream_output(full)
        result = _build_result(image_id, filename, analysis_data, processing_time, usage)
        await db.save_analysis(result.model_dump(mode="json"), location)
        await cost_guard.add(usage.get("cost_usd", 0.0))
        logger.info(
            "image_analyzed",
            image_id=image_id,
            model=settings.vision_model,
            detail_level=detail_level,
            language=language,
            streaming=True,
            duration_ms=round(processing_time, 1),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cost_usd=usage.get("cost_usd", 0.0),
        )
        yield _sse({"type": "complete", "analysis": result.model_dump(mode="json")})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ============ History & Retrieval ============


@app.get("/api/history")
async def get_history():
    """Get analysis history (most recent first)."""
    return await db.get_all()


@app.get("/api/metrics")
async def get_metrics():
    """Aggregate usage metrics: total analyses, tokens, cost, avg latency."""
    metrics = await db.get_metrics()
    metrics["model"] = settings.vision_model
    return metrics


@app.get("/api/analysis/{image_id}")
async def get_analysis(image_id: str):
    """Get the analysis metadata for an image."""
    analysis = await db.get_one(image_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return analysis


@app.delete("/api/analysis/{image_id}")
async def delete_analysis(image_id: str):
    """Delete an analysis and its stored image file."""
    location = await db.delete(image_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Image not found")
    await storage.delete(location)
    return {"deleted": image_id}


@app.get("/api/images/{image_id}")
async def get_image_file(image_id: str):
    """Serve the raw uploaded image so the frontend can display it."""
    location = await db.get_file_path(image_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Image not found")
    loaded = await storage.load(location)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Image not found")
    data, content_type = loaded
    return Response(content=data, media_type=content_type)


# ============ Export ============


@app.get("/api/export/{image_id}")
async def export_analysis(image_id: str, format: str = "json"):
    """Export an analysis as JSON or Markdown."""
    data = await db.get_one(image_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")

    if format == "json":
        return JSONResponse(data)

    if format == "markdown":
        objects_md = (
            "\n".join(
                f"- {obj['name']} (confidence: {obj['confidence']:.0%})" for obj in data["objects"]
            )
            or "_None detected_"
        )
        tags_md = ", ".join(data["tags"]) or "_None_"
        md = f"""# Analysis: {data["filename"]}

## Description
{data["description"]}

## Objects Detected
{objects_md}

## Sentiment
{data["sentiment"]}

## Tags
{tags_md}

## Extracted Text
{data["extracted_text"] or "_None_"}

---
*Analyzed at: {data["uploaded_at"]}*
*Processing time: {data["processing_time_ms"]:.0f}ms*
"""
        return JSONResponse({"markdown": md})

    raise HTTPException(status_code=400, detail="Unsupported format")


# ============ Health / status ============


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/status")
async def status():
    """Readiness/config introspection (no secrets) — which backends are active."""
    return {
        "status": "ok",
        "model": settings.vision_model,
        "storage": "s3" if settings.s3_bucket else "local",
        "database": "postgres" if "postgres" in settings.database_url else "sqlite",
        "redis_enabled": _redis is not None,
        "daily_cost_limit_usd": settings.daily_cost_limit_usd,
        "rate_limit": f"{settings.rate_limit_max}/{settings.rate_limit_window}s",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True,
    )
