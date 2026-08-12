"""Endpoint tests with the vision service mocked (no real API calls)."""


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


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


def test_export_markdown(client, png_bytes):
    created = client.post(
        "/api/analyze/image",
        files={"file": ("a.png", png_bytes, "image/png")},
    ).json()
    res = client.get(f"/api/export/{created['id']}?format=markdown")
    assert res.status_code == 200
    assert "# Analysis: a.png" in res.json()["markdown"]
