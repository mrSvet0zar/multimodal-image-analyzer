import type { Analysis, ExportFormat } from '../types';

interface Props {
  analysis: Analysis;
  apiUrl: string;
  onExport: (format: ExportFormat) => void;
}

export default function AnalysisDisplay({ analysis, apiUrl, onExport }: Props) {
  const totalTokens = analysis.input_tokens + analysis.output_tokens;

  return (
    <div className="analysis-display">
      <div className="analysis-header">
        <h2>{analysis.filename}</h2>
        <div className="export-buttons">
          <button onClick={() => onExport('json')}>📋 JSON</button>
          <button onClick={() => onExport('markdown')}>📝 Markdown</button>
        </div>
      </div>

      {analysis.media_type === 'video' && analysis.video_url ? (
        <div className="analysis-image">
          <video
            src={`${apiUrl}${analysis.video_url}`}
            poster={`${apiUrl}${analysis.image_url}`}
            controls
          />
        </div>
      ) : (
        analysis.image_url && (
          <div className="analysis-image">
            <img src={`${apiUrl}${analysis.image_url}`} alt={analysis.filename} />
          </div>
        )
      )}

      <div className="description">
        <h3>Description</h3>
        <p>{analysis.description}</p>
      </div>

      {analysis.objects.length > 0 && (
        <div className="objects">
          <h3>Objects detected</h3>
          <div className="objects-grid">
            {analysis.objects.map((obj, idx) => (
              <div key={idx} className="object-card">
                <div className="object-top">
                  <span className="name">{obj.name}</span>
                  <span className="confidence">
                    {(obj.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="confidence-bar">
                  <div
                    className="confidence-fill"
                    style={{ width: `${Math.round(obj.confidence * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="sentiment">
        <h3>Sentiment</h3>
        <p
          className={`sentiment-badge ${analysis.sentiment
            .toLowerCase()
            .replace(/\s+/g, '-')}`}
        >
          {analysis.sentiment}
        </p>
      </div>

      {analysis.tags.length > 0 && (
        <div className="tags">
          <h3>Tags</h3>
          <div className="tags-cloud">
            {analysis.tags.map((tag, idx) => (
              <span key={idx} className="tag">
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {analysis.extracted_text && (
        <div className="extracted-text">
          <h3>Extracted text</h3>
          <p>{analysis.extracted_text}</p>
        </div>
      )}

      {analysis.transcript && (
        <div className="extracted-text">
          <h3>🎙️ Transcript</h3>
          <p>{analysis.transcript}</p>
        </div>
      )}

      <div className="metadata">
        <small>
          Processed in {analysis.processing_time_ms.toFixed(0)}ms
          {totalTokens > 0 && <> · {totalTokens.toLocaleString()} tokens</>}
          {analysis.cost_usd > 0 && <> · ${analysis.cost_usd.toFixed(4)}</>}
        </small>
        {analysis.cached && <span className="cached-badge">⚡ cached · no API call</span>}
      </div>
    </div>
  );
}
