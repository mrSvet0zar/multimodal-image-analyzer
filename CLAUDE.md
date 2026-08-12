# 🤖 CLAUDE.md - Projet 3: Multi-Modal AI Project

## 📌 Objectif du Projet
Créer une application qui traite à la fois images et texte, en utilisant Claude Vision API. Démontre la maîtrise des modèles vision-language, traitement d'images, et applications pratiques multi-modales.

---

## 🛠️ Stack Technologique

### Backend
- **Framework :** FastAPI
- **LLM Vision :** Claude 3 Vision API (Anthropic)
- **Image Processing :** Pillow, opencv-python
- **File Handling :** python-multipart
- **Database :** SQLite (optionnel, pour historique)

### Frontend
- **Framework :** React 18 + Vite
- **Styling :** Tailwind CSS
- **Image Upload :** React Dropzone
- **HTTP Client :** Axios
- **UI State :** React Query

### Infrastructure
- **Backend :** Railway.app
- **Frontend :** Vercel
- **File Storage :** Local filesystem ou AWS S3

---

## 📐 Architecture

```
┌─────────────────────────────────────┐
│      Frontend (React)               │
│  ┌─────────────────────────────┐   │
│  │ Image Upload (Drag & Drop)  │   │
│  │ Analysis Display            │   │
│  │ History Panel               │   │
│  └────────────┬────────────────┘   │
│               │                    │
│          (HTTP REST)              │
│               │                    │
│  ┌────────────▼────────────────┐   │
│  │   Backend (FastAPI)         │   │
│  │  ┌────────────────────────┐ │   │
│  │  │ • Image Upload Handler │ │   │
│  │  │ • Image Validation     │ │   │
│  │  │ • Claude Vision Call   │ │   │
│  │  │ • Response Parsing     │ │   │
│  │  └────────────────────────┘ │   │
│  └────────────┬────────────────┘   │
│               │                    │
│    ┌──────────▼──────────┐         │
│    │  Claude Vision API  │         │
│    │  (Anthropic)        │         │
│    └─────────────────────┘         │
│                                    │
└────────────────────────────────────┘
```

---

## 📋 Phase 1: Backend Setup

### 1.1 Project Structure

```bash
mkdir image-analyzer
cd image-analyzer

mkdir -p backend frontend
mkdir -p backend/app/{api,models,schemas,utils}
mkdir -p backend/uploads
mkdir -p frontend/src/{components,pages,services}

cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn anthropic pillow python-multipart python-dotenv aiofiles
```

### 1.2 Environment Variables

**Backend `.env`**
```
ANTHROPIC_API_KEY=sk-ant-...
API_PORT=8000
CORS_ORIGINS=["http://localhost:5173"]
MAX_FILE_SIZE=10485760  # 10MB in bytes
UPLOAD_DIR=./uploads
```

**Frontend `.env.local`**
```
VITE_API_URL=http://localhost:8000
```

---

## 📋 Phase 2: Backend Implementation

### 2.1 Data Models & Schemas

**File: `backend/app/schemas.py`**
```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AnalysisObject(BaseModel):
    name: str
    confidence: float
    description: Optional[str] = None

class ImageAnalysis(BaseModel):
    id: str
    filename: str
    uploaded_at: datetime
    description: str
    objects: List[AnalysisObject]
    sentiment: str
    tags: List[str]
    extracted_text: str
    processing_time_ms: float
    image_url: str

class AnalysisRequest(BaseModel):
    detail_level: str = "medium"  # simple, medium, detailed
    language: str = "en"  # language for response

class BatchAnalysisRequest(BaseModel):
    detail_level: str = "medium"
    language: str = "en"
```

### 2.2 Image Analysis Service

**File: `backend/app/vision_service.py`**
```python
import anthropic
import base64
import json
from typing import Dict, Any, Optional
import os

class VisionAnalyzer:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = "claude-3-5-sonnet-20241022"
    
    async def analyze_image(
        self,
        image_data: bytes,
        detail_level: str = "medium",
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Analyze image using Claude Vision API
        
        Returns structured analysis with:
        - description
        - objects detected
        - sentiment
        - tags
        - extracted text
        """
        
        # Encode image to base64
        base64_image = base64.standard_b64encode(image_data).decode("utf-8")
        
        # Determine detail level prompt
        detail_prompts = {
            "simple": "Provide a brief (1-2 sentence) description of this image.",
            "medium": """Analyze this image and provide:
1. A clear description (2-3 sentences)
2. List of main objects detected
3. Overall sentiment or mood
4. 5-10 relevant keywords/tags
5. Any text visible in the image

Format as JSON with keys: description, objects (array of {name, confidence}), sentiment, tags, extracted_text""",
            "detailed": """Provide a comprehensive analysis of this image:
1. Detailed description (3-4 sentences)
2. All objects detected with confidence scores
3. Scene analysis (lighting, composition, style)
4. Emotional/sentiment analysis
5. Dominant colors
6. Potential use cases
7. Any text visible
8. Quality assessment

Format as JSON with keys: description, objects, scene_analysis, sentiment, colors, use_cases, extracted_text, quality_score"""
        }
        
        prompt = detail_prompts.get(detail_level, detail_prompts["medium"])
        
        # Add language instruction
        if language != "en":
            prompt += f"\n\nProvide the response in {language}."
        
        # Call Claude Vision API
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )
        
        # Extract response
        response_text = message.content[0].text
        
        # Try to parse as JSON if possible
        try:
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                analysis = json.loads(response_text[json_start:json_end])
            else:
                # Fallback if no JSON found
                analysis = {"description": response_text}
        except json.JSONDecodeError:
            analysis = {"description": response_text}
        
        # Ensure required fields exist
        analysis.setdefault("description", "")
        analysis.setdefault("objects", [])
        analysis.setdefault("sentiment", "neutral")
        analysis.setdefault("tags", [])
        analysis.setdefault("extracted_text", "")
        
        return analysis
```

### 2.3 FastAPI Routes

**File: `backend/app/main.py`**
```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from datetime import datetime
import uuid
import time
import aiofiles
from pathlib import Path
from dotenv import load_dotenv

from app.schemas import ImageAnalysis, AnalysisObject
from app.vision_service import VisionAnalyzer

load_dotenv()

app = FastAPI(title="Image Analyzer API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global vision analyzer
vision_analyzer = VisionAnalyzer()

# Create upload directory
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory storage (replace with DB in production)
analyzed_images = {}

@app.on_event("startup")
async def startup():
    """Verify API connection on startup"""
    try:
        # Test API connection with a simple text message
        response = vision_analyzer.client.messages.create(
            model=vision_analyzer.model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print("✓ Claude API connection successful")
    except Exception as e:
        print(f"✗ Claude API connection failed: {e}")

# ============ Image Upload & Analysis ============

@app.post("/api/analyze/image")
async def analyze_image(
    file: UploadFile = File(...),
    detail_level: str = "medium",
    language: str = "en"
):
    """Upload and analyze an image"""
    try:
        # Validate file size
        max_size = int(os.getenv("MAX_FILE_SIZE", 10485760))
        
        # Read file content
        content = await file.read()
        
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {max_size} bytes"
            )
        
        # Validate image type
        if file.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid image format. Supported: JPEG, PNG, GIF, WebP"
            )
        
        # Generate ID
        image_id = str(uuid.uuid4())
        
        # Save image to disk
        file_extension = file.filename.split('.')[-1]
        file_path = UPLOAD_DIR / f"{image_id}.{file_extension}"
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Analyze image
        start_time = time.time()
        
        analysis_data = await vision_analyzer.analyze_image(
            content,
            detail_level=detail_level,
            language=language
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Parse objects
        objects = []
        if "objects" in analysis_data and isinstance(analysis_data["objects"], list):
            for obj in analysis_data["objects"]:
                if isinstance(obj, dict):
                    objects.append(AnalysisObject(
                        name=obj.get("name", ""),
                        confidence=float(obj.get("confidence", 0.8)),
                        description=obj.get("description")
                    ))
                elif isinstance(obj, str):
                    objects.append(AnalysisObject(
                        name=obj,
                        confidence=0.8
                    ))
        
        # Create response
        response = ImageAnalysis(
            id=image_id,
            filename=file.filename,
            uploaded_at=datetime.utcnow(),
            description=analysis_data.get("description", ""),
            objects=objects,
            sentiment=analysis_data.get("sentiment", "neutral"),
            tags=analysis_data.get("tags", []),
            extracted_text=analysis_data.get("extracted_text", ""),
            processing_time_ms=processing_time,
            image_url=f"/api/images/{image_id}"
        )
        
        # Store in memory
        analyzed_images[image_id] = response.dict()
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error analyzing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Batch Analysis ============

@app.post("/api/analyze/batch")
async def batch_analyze(
    files: list[UploadFile] = File(...),
    detail_level: str = "medium"
):
    """Analyze multiple images"""
    results = []
    
    for file in files:
        try:
            # Reuse single analysis endpoint
            result = await analyze_image(file, detail_level)
            results.append(result)
        except Exception as e:
            results.append({"error": str(e), "filename": file.filename})
    
    return {
        "total": len(files),
        "successful": sum(1 for r in results if "error" not in r),
        "results": results
    }

# ============ History & Export ============

@app.get("/api/history")
async def get_history():
    """Get analysis history"""
    return list(analyzed_images.values())

@app.get("/api/images/{image_id}")
async def get_image(image_id: str):
    """Get analyzed image details"""
    if image_id not in analyzed_images:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return analyzed_images[image_id]

@app.get("/api/export/{image_id}")
async def export_analysis(image_id: str, format: str = "json"):
    """Export analysis in different formats"""
    if image_id not in analyzed_images:
        raise HTTPException(status_code=404, detail="Image not found")
    
    data = analyzed_images[image_id]
    
    if format == "json":
        return JSONResponse(data)
    elif format == "markdown":
        md = f"""# Analysis: {data['filename']}

## Description
{data['description']}

## Objects Detected
{chr(10).join([f"- {obj['name']} (confidence: {obj['confidence']:.2%})" for obj in data['objects']])}

## Sentiment
{data['sentiment']}

## Tags
{', '.join(data['tags'])}

## Extracted Text
{data['extracted_text']}

---
*Analyzed at: {data['uploaded_at']}*
*Processing time: {data['processing_time_ms']:.0f}ms*
"""
        return JSONResponse({"markdown": md})
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

# ============ Health Check ============

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 📋 Phase 3: Frontend Implementation

### 3.1 Main App Component

**File: `frontend/src/App.jsx`**
```jsx
import React, { useState } from 'react';
import ImageUpload from './components/ImageUpload';
import AnalysisDisplay from './components/AnalysisDisplay';
import History from './components/History';
import './App.css';

function App() {
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleImageUpload = async (file, detailLevel) => {
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('detail_level', detailLevel);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/analyze/image`,
        {
          method: 'POST',
          body: formData
        }
      );

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }

      const data = await response.json();
      setCurrentAnalysis(data);
      
      // Add to history
      setHistory(prev => [data, ...prev.slice(0, 9)]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    if (!currentAnalysis) return;

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/export/${currentAnalysis.id}?format=${format}`,
        { method: 'GET' }
      );

      const data = await response.json();
      
      // Create download
      const blob = new Blob(
        [format === 'json' ? JSON.stringify(data, null, 2) : data.markdown],
        { type: format === 'json' ? 'application/json' : 'text/markdown' }
      );
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis.${format}`;
      a.click();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🖼️ Image Analyzer</h1>
        <p>Powered by Claude Vision</p>
      </header>

      <div className="container">
        <div className="main">
          <ImageUpload onUpload={handleImageUpload} loading={loading} />
          
          {error && <div className="error-banner">{error}</div>}
          
          {loading && <div className="loading">Analyzing image...</div>}
          
          {currentAnalysis && (
            <AnalysisDisplay 
              analysis={currentAnalysis} 
              onExport={handleExport}
            />
          )}
        </div>

        <aside className="sidebar">
          <History images={history} onSelect={setCurrentAnalysis} />
        </aside>
      </div>
    </div>
  );
}

export default App;
```

### 3.2 Image Upload Component

**File: `frontend/src/components/ImageUpload.jsx`**
```jsx
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

export default function ImageUpload({ onUpload, loading }) {
  const [detailLevel, setDetailLevel] = useState('medium');
  const [preview, setPreview] = useState(null);

  const onDrop = useCallback(acceptedFiles => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      
      // Preview
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(file);
      
      // Upload
      onUpload(file, detailLevel);
    }
  }, [onUpload, detailLevel]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp'] },
    disabled: loading
  });

  return (
    <div className="image-upload">
      <div className="detail-level-selector">
        <label>Analysis Detail Level:</label>
        <select value={detailLevel} onChange={(e) => setDetailLevel(e.target.value)}>
          <option value="simple">Simple (Quick)</option>
          <option value="medium">Medium (Balanced)</option>
          <option value="detailed">Detailed (Comprehensive)</option>
        </select>
      </div>

      <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
        <input {...getInputProps()} />
        {isDragActive ? (
          <p>Drop the image here...</p>
        ) : (
          <>
            <p>Drag & drop an image here</p>
            <p>or click to select</p>
          </>
        )}
      </div>

      {preview && (
        <div className="preview">
          <img src={preview} alt="Preview" />
        </div>
      )}
    </div>
  );
}
```

### 3.3 Analysis Display Component

**File: `frontend/src/components/AnalysisDisplay.jsx`**
```jsx
import React from 'react';

export default function AnalysisDisplay({ analysis, onExport }) {
  return (
    <div className="analysis-display">
      <div className="header">
        <h2>{analysis.filename}</h2>
        <div className="export-buttons">
          <button onClick={() => onExport('json')}>📋 Export JSON</button>
          <button onClick={() => onExport('markdown')}>📝 Export MD</button>
        </div>
      </div>

      <div className="description">
        <h3>Description</h3>
        <p>{analysis.description}</p>
      </div>

      {analysis.objects && analysis.objects.length > 0 && (
        <div className="objects">
          <h3>Objects Detected</h3>
          <div className="objects-grid">
            {analysis.objects.map((obj, idx) => (
              <div key={idx} className="object-card">
                <div className="name">{obj.name}</div>
                <div className="confidence">
                  {(obj.confidence * 100).toFixed(0)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="sentiment">
        <h3>Sentiment</h3>
        <p className={`sentiment-badge ${analysis.sentiment.toLowerCase()}`}>
          {analysis.sentiment}
        </p>
      </div>

      {analysis.tags && analysis.tags.length > 0 && (
        <div className="tags">
          <h3>Tags</h3>
          <div className="tags-cloud">
            {analysis.tags.map((tag, idx) => (
              <span key={idx} className="tag">{tag}</span>
            ))}
          </div>
        </div>
      )}

      {analysis.extracted_text && (
        <div className="extracted-text">
          <h3>Extracted Text</h3>
          <p>{analysis.extracted_text}</p>
        </div>
      )}

      <div className="metadata">
        <small>Processed in {analysis.processing_time_ms.toFixed(0)}ms</small>
      </div>
    </div>
  );
}
```

---

## 📋 Phase 4: Styling

**File: `frontend/src/App.css`**
```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

.app {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  text-align: center;
  color: white;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
}

.container {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
}

.main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.image-upload {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}

.dropzone {
  border: 3px dashed #667eea;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.dropzone.active {
  border-color: #764ba2;
  background: #f5f5f5;
}

.dropzone p {
  margin: 10px 0;
  color: #666;
}

.analysis-display {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}

.analysis-display h3 {
  margin-top: 20px;
  margin-bottom: 10px;
  color: #333;
}

.objects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
}

.object-card {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 8px;
  text-align: center;
}

.tags-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tag {
  background: #667eea;
  color: white;
  padding: 5px 15px;
  border-radius: 20px;
  font-size: 0.9rem;
}

.sidebar {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
  height: fit-content;
}

@media (max-width: 768px) {
  .container {
    grid-template-columns: 1fr;
  }
  
  .header h1 {
    font-size: 1.8rem;
  }
}
```

---

## 📋 Phase 5: Deployment

### 5.1 Backend (Railway)

```bash
# Setup Railway
railway login
railway init

# Deploy
git push

# View logs
railway logs
```

### 5.2 Frontend (Vercel)

```bash
npm run build
vercel deploy --prod
```

---

## ✅ Checklist de Développement

- [ ] Backend setup & dependencies
- [ ] Environment variables configured
- [ ] Vision service implementation
- [ ] FastAPI routes complete
- [ ] Image upload handling
- [ ] Analysis response parsing
- [ ] Frontend React setup
- [ ] Image upload component
- [ ] Analysis display component
- [ ] History management
- [ ] Export functionality
- [ ] Responsive styling
- [ ] Error handling
- [ ] Testing flows
- [ ] Deployment to Railway
- [ ] Deployment to Vercel
- [ ] Documentation

---

## 🎯 Critères de Succès

✅ Upload image → Analysis < 3 secondes  
✅ Affichage responsive et intuitif  
✅ Export JSON & Markdown  
✅ Historique persistent  
✅ Démonstration avec 5+ images différentes  
✅ GitHub repo avec README  
✅ Lien de démo public  

---

**📅 Timeline estimée: 2-3 semaines**

Bonne chance! 🎯
