# 🖼️ Image Analyzer — Multi-Modal AI

A full-stack application that analyzes images with **Claude Vision**. Upload an
image and get back a structured analysis: description, detected objects, sentiment,
tags, and any extracted text. Results can be exported as JSON or Markdown, and a
history panel keeps your recent analyses.

**Stack:** FastAPI + Anthropic Claude Vision (backend) · React 18 + Vite (frontend)

### 🔗 Live demo

- **App:** https://multimodal-image-analyzer.vercel.app
- **API:** https://multimodal-image-analyzer-production.up.railway.app/docs

> Frontend on Vercel · Backend on Railway. Uploads and history are stored in
> memory on the free tier, so they reset when the backend restarts.

---

## Features

- 🖱️ Drag & drop image upload (JPEG, PNG, GIF, WebP)
- 🎚️ Three detail levels: simple / medium / detailed
- 🧠 Structured analysis via Claude Vision (`claude-sonnet-5`)
- 🏷️ Objects with confidence, sentiment, tags, extracted text
- 📦 Batch analysis endpoint
- 📤 Export as JSON or Markdown
- 🕑 Session history with thumbnails

---

## Project structure

```
multimodal/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI routes
│   │   ├── vision_service.py  # Claude Vision integration
│   │   └── schemas.py         # Pydantic models
│   ├── uploads/               # Stored images (gitignored)
│   ├── requirements.txt
│   └── .env                   # Your secrets (gitignored)
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── App.css
    │   └── components/
    │       ├── ImageUpload.jsx
    │       ├── AnalysisDisplay.jsx
    │       └── History.jsx
    └── package.json
```

---

## Getting started

### 1. Backend

```bash
cd backend
python -m venv venv
# Windows PowerShell:
venv\Scripts\Activate.ps1
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

Add your Anthropic API key to `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Run the server:

```bash
uvicorn app.main:app --reload --port 8000
```

API docs are available at http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## API reference

| Method | Endpoint                     | Description                          |
| ------ | ---------------------------- | ------------------------------------ |
| POST   | `/api/analyze/image`         | Analyze a single image               |
| POST   | `/api/analyze/batch`         | Analyze multiple images              |
| GET    | `/api/history`               | List analyzed images (recent first)  |
| GET    | `/api/analysis/{id}`         | Analysis metadata for one image      |
| GET    | `/api/images/{id}`           | Serve the raw uploaded image         |
| GET    | `/api/export/{id}?format=`   | Export analysis (`json` / `markdown`)|
| GET    | `/health`                    | Health check                         |

Query params for analysis: `detail_level` (`simple`|`medium`|`detailed`), `language`.

---

## Notes

- Analyses are stored **in memory** — they reset when the backend restarts.
  Swap `analyzed_images` in `main.py` for SQLite/Postgres to persist.
- The Claude model is set via `VISION_MODEL` in `.env` (default `claude-sonnet-5`).
