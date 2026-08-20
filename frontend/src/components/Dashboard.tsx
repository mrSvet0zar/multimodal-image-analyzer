import type { Metrics } from '../types';

interface Props {
  metrics?: Metrics;
  loading?: boolean;
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-tile">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export default function Dashboard({ metrics, loading }: Props) {
  if (loading || !metrics) {
    return (
      <div className="dashboard">
        <div className="loading">
          <div className="spinner" />
          Loading metrics…
        </div>
      </div>
    );
  }

  const totalTokens = metrics.total_input_tokens + metrics.total_output_tokens;
  const maxCount = Math.max(1, ...metrics.by_day.map((d) => d.count));

  return (
    <div className="dashboard">
      <div className="stat-grid">
        <Tile label="Analyses" value={metrics.total_analyses.toLocaleString()} />
        <Tile label="Tokens" value={totalTokens.toLocaleString()} />
        <Tile label="Cost" value={`$${metrics.total_cost_usd.toFixed(4)}`} />
        <Tile
          label="Avg latency"
          value={`${Math.round(metrics.avg_processing_time_ms)} ms`}
        />
        <Tile label="Model" value={metrics.model} />
      </div>

      <div className="chart-card">
        <h3>Analyses per day</h3>
        {metrics.by_day.length === 0 ? (
          <p className="history-empty">No data yet — analyze an image to get started.</p>
        ) : (
          <div className="bar-chart">
            {metrics.by_day.map((d) => (
              <div
                className="bar-col"
                key={d.day}
                title={`${d.day}: ${d.count} analyses · $${d.cost_usd.toFixed(4)}`}
              >
                <div className="bar-value">{d.count}</div>
                <div
                  className="bar"
                  style={{ height: `${(d.count / maxCount) * 100}%` }}
                />
                <div className="bar-label">{d.day.slice(5)}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
