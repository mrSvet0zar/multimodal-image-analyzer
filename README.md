# 🖼️ Image Analyzer — IA Multi-Modale

Une application full-stack qui analyse des images avec **Claude Vision**. On
téléverse une image et on récupère une analyse structurée : description, objets
détectés, sentiment, tags et texte extrait. Les résultats s'exportent en JSON ou
Markdown, et un panneau d'historique conserve les analyses récentes.

**Stack :** FastAPI + Claude Vision d'Anthropic (backend) · React 18 + **TypeScript** + Vite + **React Query** (frontend)

[![CI](https://github.com/mrSvet0zar/multimodal-image-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/mrSvet0zar/multimodal-image-analyzer/actions/workflows/ci.yml)

### 🔗 Démo en ligne

- **App :** https://multimodal-image-analyzer.vercel.app
- **API :** https://multimodal-image-analyzer-production.up.railway.app/docs

> Frontend sur Vercel · Backend sur Railway (build Nixpacks + volume persistant
> pour SQLite et les images).

---

## Fonctionnalités

- 🖱️ Téléversement par glisser-déposer (JPEG, PNG, GIF, WebP)
- 🎚️ Trois niveaux de détail : simple / medium / detailed
- 🧠 **Sortie structurée garantie** via tool-use Claude (schéma strict, pas de parsing fragile)
- ⚡ Streaming en temps réel (SSE) : la description s'affiche au fil de l'eau
- 🏷️ Objets avec score de confiance, sentiment, tags, texte extrait
- 🌍 Analyse dans 8 langues (sélecteur dans l'UI)
- 📦 Upload multiple + endpoint d'analyse par lot (batch)
- 🔍 Recherche/filtre dans l'historique
- 📤 Export en JSON ou Markdown
- 🕑 Historique **persistant** (SQLite) avec vignettes
- 🛡️ Validation + redimensionnement d'image (Pillow), rate limiting par IP
- 🔁 **Résilience** : retries/backoff + timeout + modèle de fallback
- 📊 **Observabilité** : tokens & coût par appel, logs JSON avec request-id, `/api/metrics`
- ✅ **Évaluations** : dataset golden + scoring automatisé avec seuil
- 🌙 Dark mode (persistant, suit la préférence système) + micro-animations
- 🧪 34 tests (pytest), lint **ruff** + types **mypy**, **CI GitHub Actions**, **Docker**

---

## Structure du projet

```
multimodal/
├── backend/
│   ├── app/
│   │   ├── main.py            # Routes FastAPI + middleware (request-id, logs)
│   │   ├── vision_service.py  # Claude Vision : tool-use + streaming + fallback
│   │   ├── config.py          # Config typée (pydantic-settings)
│   │   ├── cost.py            # Estimation tokens/coût
│   │   ├── logging_setup.py   # Logs JSON structurés (structlog)
│   │   ├── image_utils.py     # Validation + redimensionnement (Pillow)
│   │   ├── rate_limit.py      # Rate limiting par IP
│   │   ├── db.py             # Persistance SQLite (aiosqlite) + métriques
│   │   └── schemas.py         # Modèles Pydantic
│   ├── evals/                 # Dataset golden + scoring (run_evals.py)
│   ├── tests/                 # 34 tests pytest
│   ├── Dockerfile.local       # Image backend (docker compose ; Railway = Nixpacks)
│   ├── ruff.toml · mypy.ini · pytest.ini
│   └── requirements.txt · requirements-dev.txt
├── frontend/                  # React 18 + TypeScript + React Query
│   ├── src/
│   │   ├── App.tsx · main.tsx · ErrorBoundary.tsx
│   │   ├── api.ts · types.ts   # couche API typée + modèles
│   │   └── components/*.tsx
│   ├── Dockerfile             # build multi-stage → nginx
│   └── package.json
├── .github/workflows/ci.yml   # Lint + types + tests + build
└── docker-compose.yml         # Stack complète en local
```

---

## Démarrage

### 1. Backend

```bash
cd backend
python -m venv venv
# Windows PowerShell :
venv\Scripts\Activate.ps1
# macOS/Linux :
# source venv/bin/activate

pip install -r requirements.txt
```

Ajoute ta clé API Anthropic dans `backend/.env` :

```
ANTHROPIC_API_KEY=sk-ant-...
```

Lance le serveur :

```bash
uvicorn app.main:app --reload --port 8000
```

La documentation interactive de l'API est disponible sur http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Ouvre http://localhost:5173

### 3. Qualité (backend)

```bash
cd backend
pip install -r requirements-dev.txt
ruff check .        # lint
ruff format --check .
mypy                # types
pytest              # 34 tests (service Vision mocké, aucun appel API réel)
```

Les tests couvrent le traitement d'image, la couche SQLite, le rate limiter, le
calcul de coût, le scoring des evals et tous les endpoints (streaming inclus).

### 4. Docker (stack complète en local)

```bash
ANTHROPIC_API_KEY=sk-ant-... docker compose up --build
```

Backend + frontend + volume de données, puis http://localhost:5173.

---

## Référence de l'API

| Méthode | Endpoint                     | Description                              |
| ------- | ---------------------------- | ---------------------------------------- |
| POST    | `/api/analyze/image`         | Analyser une seule image                 |
| POST    | `/api/analyze/stream`        | Analyser une image en streaming (SSE)    |
| POST    | `/api/analyze/batch`         | Analyser plusieurs images                |
| GET     | `/api/history`               | Lister les images analysées (récentes)   |
| GET     | `/api/metrics`               | Métriques agrégées (analyses, tokens, coût) |
| GET     | `/api/analysis/{id}`         | Métadonnées d'analyse d'une image        |
| GET     | `/api/images/{id}`           | Servir l'image téléversée brute          |
| GET     | `/api/export/{id}?format=`   | Exporter l'analyse (`json` / `markdown`) |
| GET     | `/health`                    | Vérification de l'état                    |

Paramètres de requête pour l'analyse : `detail_level` (`simple`|`medium`|`detailed`), `language`.

---

## Ingénierie « production-ready »

- **Sortie structurée garantie** — l'analyse passe par un *tool-use* Claude à
  schéma strict ([`vision_service.py`](backend/app/vision_service.py)) : le JSON
  est toujours valide, sans parsing défensif.
- **Résilience** — client configuré avec `timeout` + `max_retries` (backoff), et
  un `VISION_FALLBACK_MODEL` optionnel essayé si le modèle principal est saturé.
- **Observabilité** — chaque appel logge tokens, coût (€ estimé), latence et
  modèle en **JSON structuré** ([`logging_setup.py`](backend/app/logging_setup.py))
  avec un **request-id** de corrélation ; agrégats via `GET /api/metrics`.
- **Config typée** — `pydantic-settings` ([`config.py`](backend/app/config.py)),
  source unique validée au démarrage.
- **Persistance** — SQLite via `aiosqlite` ; en prod, un volume Railway au
  `/data` (voir Déploiement).

### Évaluations (evals)

Un dataset « golden » d'images générées avec vérité terrain connue, scoré
automatiquement contre les sorties du modèle, avec seuil de réussite :

```bash
cd backend
python -m evals.run_evals --threshold 0.75
```

Utile pour mesurer l'impact d'un changement de prompt/modèle. Lançable à la
demande en CI (job manuel « Evals »).

### CI/CD

[GitHub Actions](.github/workflows/ci.yml) sur chaque push/PR : `ruff` (lint +
format), `mypy` (types), `pytest`, et build du frontend. Pre-commit hooks
disponibles (`pre-commit install`).

---

## Déploiement

- **Backend (Railway) :** Root Directory = `backend`, démarrage via `backend/railway.json`.
  Variables d'environnement à définir dans le dashboard (`ANTHROPIC_API_KEY`,
  `VISION_MODEL`, `CORS_ORIGINS` = l'URL Vercel, `MAX_FILE_SIZE`).
  Railway fournit `PORT` automatiquement.
- **Frontend (Vercel) :** Root Directory = `frontend`, variable `VITE_API_URL` = l'URL Railway.
- Un push sur `main` redéploie automatiquement les deux services.

> ⚠️ Railway (Root Directory = `backend`) construit un `backend/Dockerfile` s'il
> en trouve un, au lieu d'utiliser Nixpacks. L'image Docker locale est donc
> nommée `Dockerfile.local` — ne pas la renommer en `Dockerfile`.

### ⚠️ Persistance en production (Railway Volume)

Le système de fichiers d'un conteneur Railway est **éphémère** : sans volume, la
base SQLite et les images sont réinitialisées à chaque redéploiement. Pour une
persistance réelle :

1. Railway → service backend → **Volumes** → **New Volume**, mount path : `/data`
2. Dans **Variables**, pointer la base et les uploads vers le volume :
   ```
   DB_PATH=/data/analyses.db
   UPLOAD_DIR=/data/uploads
   ```
3. Redéployer. L'historique et les images survivent désormais aux redéploiements.

En local, les valeurs par défaut (`./analyses.db`, `./uploads`) suffisent.
