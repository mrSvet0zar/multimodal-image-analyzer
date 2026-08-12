# 🖼️ Image Analyzer — IA Multi-Modale

Une application full-stack qui analyse des images avec **Claude Vision**. On
téléverse une image et on récupère une analyse structurée : description, objets
détectés, sentiment, tags et texte extrait. Les résultats s'exportent en JSON ou
Markdown, et un panneau d'historique conserve les analyses récentes.

**Stack :** FastAPI + Claude Vision d'Anthropic (backend) · React 18 + Vite (frontend)

### 🔗 Démo en ligne

- **App :** https://multimodal-image-analyzer.vercel.app
- **API :** https://multimodal-image-analyzer-production.up.railway.app/docs

> Frontend sur Vercel · Backend sur Railway. Les images et l'historique sont
> stockés en mémoire sur l'offre gratuite : ils sont réinitialisés à chaque
> redémarrage du backend.

---

## Fonctionnalités

- 🖱️ Téléversement par glisser-déposer (JPEG, PNG, GIF, WebP)
- 🎚️ Trois niveaux de détail : simple / medium / detailed
- 🧠 Analyse structurée via Claude Vision (`claude-sonnet-5`)
- 🏷️ Objets avec score de confiance, sentiment, tags, texte extrait
- 📦 Endpoint d'analyse par lot (batch)
- 📤 Export en JSON ou Markdown
- 🕑 Historique de session avec vignettes

---

## Structure du projet

```
multimodal/
├── backend/
│   ├── app/
│   │   ├── main.py            # Routes FastAPI
│   │   ├── vision_service.py  # Intégration Claude Vision
│   │   └── schemas.py         # Modèles Pydantic
│   ├── uploads/               # Images stockées (ignoré par git)
│   ├── requirements.txt
│   └── .env                   # Tes secrets (ignoré par git)
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

---

## Référence de l'API

| Méthode | Endpoint                     | Description                              |
| ------- | ---------------------------- | ---------------------------------------- |
| POST    | `/api/analyze/image`         | Analyser une seule image                 |
| POST    | `/api/analyze/batch`         | Analyser plusieurs images                |
| GET     | `/api/history`               | Lister les images analysées (récentes)   |
| GET     | `/api/analysis/{id}`         | Métadonnées d'analyse d'une image        |
| GET     | `/api/images/{id}`           | Servir l'image téléversée brute          |
| GET     | `/api/export/{id}?format=`   | Exporter l'analyse (`json` / `markdown`) |
| GET     | `/health`                    | Vérification de l'état                    |

Paramètres de requête pour l'analyse : `detail_level` (`simple`|`medium`|`detailed`), `language`.

---

## Notes

- Les analyses sont stockées **en mémoire** — elles disparaissent au redémarrage
  du backend. Remplacer `analyzed_images` dans `main.py` par SQLite/Postgres pour
  les rendre persistantes.
- Le modèle Claude se configure via `VISION_MODEL` dans `.env`
  (défaut : `claude-sonnet-5`).

---

## Déploiement

- **Backend (Railway) :** Root Directory = `backend`, démarrage via `backend/railway.json`.
  Variables d'environnement à définir dans le dashboard (`ANTHROPIC_API_KEY`,
  `VISION_MODEL`, `CORS_ORIGINS` = l'URL Vercel, `MAX_FILE_SIZE`).
  Railway fournit `PORT` automatiquement.
- **Frontend (Vercel) :** Root Directory = `frontend`, variable `VITE_API_URL` = l'URL Railway.
- Un push sur `main` redéploie automatiquement les deux services.

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
