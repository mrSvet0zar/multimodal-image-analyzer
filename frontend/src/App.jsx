import React, { useState, useEffect } from 'react';
import ImageUpload from './components/ImageUpload';
import AnalysisDisplay from './components/AnalysisDisplay';
import History from './components/History';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load the persisted history from the backend on first render.
  useEffect(() => {
    fetch(`${API_URL}/api/history`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setHistory(Array.isArray(data) ? data : []))
      .catch(() => {
        /* backend offline — start with an empty history */
      });
  }, []);

  const handleUpload = async (files, detailLevel, language) => {
    setLoading(true);
    setError(null);

    const query = `detail_level=${detailLevel}&language=${language}`;

    try {
      if (files.length === 1) {
        const formData = new FormData();
        formData.append('file', files[0]);

        const response = await fetch(`${API_URL}/api/analyze/image?${query}`, {
          method: 'POST',
          body: formData,
        });
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail || `Error: ${response.status}`);
        }

        const data = await response.json();
        setCurrentAnalysis(data);
        setHistory((prev) => [data, ...prev]);
      } else {
        const formData = new FormData();
        files.forEach((f) => formData.append('files', f));

        const response = await fetch(`${API_URL}/api/analyze/batch?${query}`, {
          method: 'POST',
          body: formData,
        });
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail || `Error: ${response.status}`);
        }

        const data = await response.json();
        const ok = (data.results || []).filter((r) => !r.error);
        const failed = (data.results || []).filter((r) => r.error);

        if (ok.length > 0) {
          setCurrentAnalysis(ok[0]);
          setHistory((prev) => [...ok, ...prev]);
        }
        if (failed.length > 0) {
          setError(
            `${failed.length} image(s) failed: ${failed
              .map((f) => f.filename)
              .join(', ')}`
          );
        }
      }
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
        `${API_URL}/api/export/${currentAnalysis.id}?format=${format}`
      );
      const data = await response.json();

      const blob = new Blob(
        [format === 'json' ? JSON.stringify(data, null, 2) : data.markdown],
        { type: format === 'json' ? 'application/json' : 'text/markdown' }
      );

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis-${currentAnalysis.id.slice(0, 8)}.${format === 'json' ? 'json' : 'md'}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      const response = await fetch(`${API_URL}/api/analysis/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error(`Error: ${response.status}`);

      setHistory((prev) => prev.filter((img) => img.id !== id));
      setCurrentAnalysis((cur) => (cur?.id === id ? null : cur));
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
          <ImageUpload onUpload={handleUpload} loading={loading} />

          {error && <div className="error-banner">⚠️ {error}</div>}

          {loading && (
            <div className="loading">
              <div className="spinner" />
              Analyzing…
            </div>
          )}

          {currentAnalysis && !loading && (
            <AnalysisDisplay
              analysis={currentAnalysis}
              apiUrl={API_URL}
              onExport={handleExport}
            />
          )}
        </div>

        <aside className="sidebar">
          <History
            images={history}
            apiUrl={API_URL}
            onSelect={setCurrentAnalysis}
            onDelete={handleDelete}
            activeId={currentAnalysis?.id}
          />
        </aside>
      </div>
    </div>
  );
}

export default App;
