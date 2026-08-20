import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import ImageUpload from './components/ImageUpload';
import AnalysisDisplay from './components/AnalysisDisplay';
import History from './components/History';
import Dashboard from './components/Dashboard';
import {
  API_URL,
  analyzeBatch,
  analyzeStream,
  analyzeVideo,
  deleteAnalysis,
  exportAnalysis,
  fetchHistory,
  fetchMetrics,
} from './api';
import { isBatchError, type Analysis, type DetailLevel, type ExportFormat } from './types';

type Theme = 'light' | 'dark';
type View = 'analyzer' | 'dashboard';

function App() {
  const queryClient = useQueryClient();

  const [currentAnalysis, setCurrentAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [streamText, setStreamText] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [view, setView] = useState<View>('analyzer');
  const [theme, setTheme] = useState<Theme>(
    () =>
      (document.documentElement.dataset.theme as Theme) ||
      (localStorage.getItem('theme') as Theme) ||
      'light',
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'));

  const { data: history = [] } = useQuery({
    queryKey: ['history'],
    queryFn: fetchHistory,
  });

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: fetchMetrics,
    enabled: view === 'dashboard',
  });

  const invalidateHistory = () => {
    queryClient.invalidateQueries({ queryKey: ['history'] });
    queryClient.invalidateQueries({ queryKey: ['metrics'] });
  };

  const batchMutation = useMutation({
    mutationFn: (vars: { files: File[]; detailLevel: DetailLevel; language: string }) =>
      analyzeBatch(vars.files, vars.detailLevel, vars.language),
    onSuccess: (data) => {
      const ok = data.results.filter((r): r is Analysis => !isBatchError(r));
      const failed = data.results.filter(isBatchError);
      if (ok.length > 0) setCurrentAnalysis(ok[0]);
      if (failed.length > 0) {
        setError(
          `${failed.length} image(s) failed: ${failed
            .map((f) => f.filename)
            .join(', ')}`,
        );
      }
      invalidateHistory();
    },
    onError: (e: Error) => setError(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAnalysis,
    onSuccess: (_data, id) => {
      setCurrentAnalysis((cur) => (cur?.id === id ? null : cur));
      invalidateHistory();
    },
    onError: (e: Error) => setError(e.message),
  });

  const videoMutation = useMutation({
    mutationFn: (vars: { file: File; detailLevel: DetailLevel; language: string }) =>
      analyzeVideo(vars.file, vars.detailLevel, vars.language),
    onSuccess: (data) => {
      setCurrentAnalysis(data);
      invalidateHistory();
    },
    onError: (e: Error) => setError(e.message),
  });

  const handleUpload = async (
    files: File[],
    detailLevel: DetailLevel,
    language: string,
  ) => {
    setError(null);

    if (files.length === 1 && files[0].type.startsWith('video/')) {
      setCurrentAnalysis(null);
      videoMutation.mutate({ file: files[0], detailLevel, language });
      return;
    }

    if (files.length === 1) {
      setStreaming(true);
      setStreamText('');
      setCurrentAnalysis(null);
      try {
        await analyzeStream(files[0], detailLevel, language, {
          onDelta: (text) => setStreamText((prev) => prev + text),
          onComplete: (analysis) => {
            setCurrentAnalysis(analysis);
            invalidateHistory();
          },
        });
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setStreaming(false);
      }
    } else {
      batchMutation.mutate({ files, detailLevel, language });
    }
  };

  const handleExport = async (format: ExportFormat) => {
    if (!currentAnalysis) return;
    try {
      const data = await exportAnalysis(currentAnalysis.id, format);
      const content =
        format === 'json' ? JSON.stringify(data, null, 2) : (data.markdown ?? '');
      const blob = new Blob([content], {
        type: format === 'json' ? 'application/json' : 'text/markdown',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis-${currentAnalysis.id.slice(0, 8)}.${format === 'json' ? 'json' : 'md'}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const loading = streaming || batchMutation.isPending || videoMutation.isPending;

  return (
    <div className="app">
      <header className="header">
        <div className="header-titles">
          <h1>
            <span className="logo">🖼️</span>{' '}
            <span className="gradient-text">Image Analyzer</span>
          </h1>
          <p>Powered by Claude Vision</p>
        </div>
        <div className="header-actions">
          <nav className="tabs">
            <button
              className={view === 'analyzer' ? 'active' : ''}
              onClick={() => setView('analyzer')}
            >
              Analyzer
            </button>
            <button
              className={view === 'dashboard' ? 'active' : ''}
              onClick={() => setView('dashboard')}
            >
              Dashboard
            </button>
          </nav>
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      {view === 'dashboard' ? (
        <Dashboard metrics={metrics} loading={metricsLoading} />
      ) : (
        <div className="container">
          <div className="main">
            <ImageUpload onUpload={handleUpload} loading={loading} />

            {error && <div className="error-banner">⚠️ {error}</div>}

            {streaming && (
              <div className="analysis-display streaming-card">
                <div className="streaming-header">
                  <span className="live-dot" />
                  Analyzing…
                </div>
                <p className="streaming-text">
                  {streamText}
                  <span className="stream-cursor">▋</span>
                </p>
              </div>
            )}

            {loading && !streaming && (
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
              onDelete={(id) => deleteMutation.mutate(id)}
              activeId={currentAnalysis?.id}
            />
          </aside>
        </div>
      )}
    </div>
  );
}

export default App;
