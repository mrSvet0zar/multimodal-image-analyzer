import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import Dashboard from './Dashboard';
import type { Metrics } from '../types';

const metrics: Metrics = {
  total_analyses: 12,
  total_input_tokens: 9000,
  total_output_tokens: 3000,
  total_cost_usd: 0.0864,
  avg_processing_time_ms: 4820,
  model: 'claude-sonnet-5',
  by_day: [
    { day: '2026-08-19', count: 5, cost_usd: 0.036 },
    { day: '2026-08-20', count: 7, cost_usd: 0.0504 },
  ],
};

describe('Dashboard', () => {
  it('shows a loading state when metrics are absent', () => {
    render(<Dashboard loading />);
    expect(screen.getByText(/Loading metrics/)).toBeInTheDocument();
  });

  it('renders the KPI tiles', () => {
    render(<Dashboard metrics={metrics} />);
    expect(screen.getByText('12')).toBeInTheDocument(); // analyses
    expect(screen.getByText('$0.0864')).toBeInTheDocument(); // cost
    expect(screen.getByText('claude-sonnet-5')).toBeInTheDocument();
    expect(screen.getByText('4820 ms')).toBeInTheDocument();
  });

  it('renders a bar per day', () => {
    const { container } = render(<Dashboard metrics={metrics} />);
    expect(container.querySelectorAll('.bar-col')).toHaveLength(2);
    // tallest bar (count 7) is full height; the other is proportional
    const bars = container.querySelectorAll<HTMLElement>('.bar');
    expect(bars[1].style.height).toBe('100%');
  });
});
