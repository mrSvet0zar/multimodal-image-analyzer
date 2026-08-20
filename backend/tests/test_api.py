"""Endpoint tests with the vision service mocked (no real API calls)."""

import json


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "redis_enabled" in body
    assert "daily_cost_limit_usd" in body
    assert body["storage"] in ("s3", "local")


def test_security_headers(client):
    res = client.get("/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "X-Request-ID" in res.headers


def test_analyze_image_ok(client, png_bytes):
    res = client.post(
        "/api/analyze/image",
        files={"file": ("photo.png", png_bytes, "image/png")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "photo.png"
    assert data["description"] == "a test image"
    assert data["objects"][0]["name"] == "square"
    assert data["tags"] == ["test", "unit"]
    assert data["image_url"].startswith("/api/images/")
    assert data["input_tokens"] == 100
    assert data["output_tokens"] == 50
    assert data["cost_usd"] == 0.00105


def test_cost_guard_blocks_endpoint(client, png_bytes, monkeypatch):
    from app import main
    from app.cost_guard import InMemoryCostGuard

    # Sample usage costs $0.00105; a $0.001 daily cap blocks the 2nd analysis.
    monkeypatch.setattr(main, "cost_guard", InMemoryCostGuard(0.001))

    first = client.post("/api/analyze/image", files={"file": ("a.png", png_bytes, "image/png")})
    assert first.status_code == 200

    second = client.post("/api/analyze/image", files={"file": ("b.png", png_bytes, "image/png")})
    assert second.status_code == 429


def test_metrics(client, png_bytes):
    assert client.get("/api/metrics").json()["total_analyses"] == 0

    client.post(
        "/api/analyze/image",
        files={"file": ("a.png", png_bytes, "image/png")},
    )

    metrics = client.get("/api/metrics").json()
    assert metrics["total_analyses"] == 1
    assert metrics["total_input_tokens"] == 100
    assert metrics["total_output_tokens"] == 50
    assert round(metrics["total_cost_usd"], 5) == 0.00105
    assert isinstance(metrics["by_day"], list)
    assert len(metrics["by_day"]) == 1
    assert metrics["by_day"][0]["count"] == 1


def test_analyze_rejects_non_image(client):
    res = client.post(
        "/api/analyze/image",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 400


def test_analyze_rejects_corrupt_image(client):
    res = client.post(
        "/api/analyze/image",
        files={"file": ("fake.png", b"not really a png", "image/png")},
    )
    assert res.status_code == 400


def test_analyze_rejects_empty_file(client):
    res = client.post(
        "/api/analyze/image",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert res.status_code == 400


def test_history_and_delete_flow(client, png_bytes):
    # Initially empty
    assert client.get("/api/history").json() == []

    # Analyze one image
    created = client.post(
        "/api/analyze/image",
        files={"file": ("a.png", png_bytes, "image/png")},
    ).json()
    image_id = created["id"]

    # History now has it
    history = client.get("/api/history").json()
    assert len(history) == 1
    assert history[0]["id"] == image_id

    # It's retrievable and the raw image is served
    assert client.get(f"/api/analysis/{image_id}").status_code == 200
    assert client.get(f"/api/images/{image_id}").status_code == 200

    # Delete it
    assert client.delete(f"/api/analysis/{image_id}").status_code == 200
    assert client.get("/api/history").json() == []
    assert client.get(f"/api/analysis/{image_id}").status_code == 404


def test_get_missing_analysis_404(client):
    assert client.get("/api/analysis/does-not-exist").status_code == 404


def test_delete_missing_analysis_404(client):
    assert client.delete("/api/analysis/does-not-exist").status_code == 404


def test_batch_analyze(client, png_bytes):
    res = client.post(
        "/api/analyze/batch",
        files=[
            ("files", ("a.png", png_bytes, "image/png")),
            ("files", ("b.png", png_bytes, "image/png")),
        ],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert data["successful"] == 2


def test_analyze_stream(client, png_bytes):
    from app import main

    async def fake_stream(*args, **kwargs):
        for chunk in [
            "A red square on white. ",
            "###DATA###",
            '{"objects":[{"name":"square","confidence":0.9}],'
            '"sentiment":"neutral","tags":["red","square"],"extracted_text":""}',
        ]:
            yield chunk
        yield {"__usage__": {"input_tokens": 80, "output_tokens": 40, "cost_usd": 0.00084}}

    main.vision_analyzer.stream_analyze_image = fake_stream

    res = client.post(
        "/api/analyze/stream",
        files={"file": ("a.png", png_bytes, "image/png")},
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    events = [
        json.loads(block.strip()[len("data:") :].strip())
        for block in res.text.split("\n\n")
        if block.strip().startswith("data:")
    ]
    types = [e["type"] for e in events]
    assert types[0] == "start"
    assert "delta" in types
    assert types[-1] == "complete"

    # Description streamed as prose; marker and JSON never leak into deltas.
    streamed = "".join(e["text"] for e in events if e["type"] == "delta")
    assert "A red square on white." in streamed
    assert "###DATA###" not in streamed
    assert "{" not in streamed

    analysis = events[-1]["analysis"]
    assert analysis["description"] == "A red square on white."
    assert analysis["objects"][0]["name"] == "square"
    assert analysis["tags"] == ["red", "square"]
    assert analysis["input_tokens"] == 80
    assert analysis["cost_usd"] == 0.00084

    # Persisted to history.
    assert len(client.get("/api/history").json()) == 1


def test_export_markdown(client, png_bytes):
    created = client.post(
        "/api/analyze/image",
        files={"file": ("a.png", png_bytes, "image/png")},
    ).json()
    res = client.get(f"/api/export/{created['id']}?format=markdown")
    assert res.status_code == 200
    assert "# Analysis: a.png" in res.json()["markdown"]
