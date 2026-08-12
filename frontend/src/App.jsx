import React, { useState } from 'react';
import ImageUpload from './components/ImageUpload';
import AnalysisDisplay from './components/AnalysisDisplay';
import History from './components/History';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

    try {
      const response = await fetch(
        `${API_URL}/api/analyze/image?detail_level=${detailLevel}`,
        { method: 'POST', body: formData }
      );

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Error: ${response.status}`);
      }

      const data = await response.json();
      setCurrentAnalysis(data);
      setHistory((prev) => [data, ...prev.slice(0, 9)]);
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

  return (
    <div className="app">
      <header className="header">
        <h1>🖼️ Image Analyzer</h1>
        <p>Powered by Claude Vision</p>
      </header>

      <div className="container">
        <div className="main">
          <ImageUpload onUpload={handleImageUpload} loading={loading} />

          {error && <div className="error-banner">⚠️ {error}</div>}

          {loading && (
            <div className="loading">
              <div className="spinner" />
              Analyzing image…
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
            activeId={currentAnalysis?.id}
          />
        </aside>
      </div>
    </div>
  );
}

export default App;
