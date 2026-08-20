import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AnalysisDisplay from './AnalysisDisplay';
import type { Analysis } from '../types';

const analysis: Analysis = {
  id: 'id-1',
  filename: 'photo.png',
  uploaded_at: '2026-08-20T10:00:00Z',
  description: 'A friendly dog in a park',
  objects: [{ name: 'dog', confidence: 0.97 }],
  sentiment: 'happy',
  tags: ['animal', 'outdoor'],
  extracted_text: 'HELLO',
  processing_time_ms: 1234,
  input_tokens: 900,
  output_tokens: 300,
  cost_usd: 0.0072,
  image_url: '/api/images/id-1',
};

describe('AnalysisDisplay', () => {
  it('renders the core analysis fields', () => {
    render(<AnalysisDisplay analysis={analysis} apiUrl="http://x" onExport={() => {}} />);

    expect(screen.getByText('photo.png')).toBeInTheDocument();
    expect(screen.getByText('A friendly dog in a park')).toBeInTheDocument();
    expect(screen.getByText('dog')).toBeInTheDocument();
    expect(screen.getByText('97%')).toBeInTheDocument();
    expect(screen.getByText('animal')).toBeInTheDocument();
    expect(screen.getByText('HELLO')).toBeInTheDocument();
  });

  it('shows the token and cost metadata', () => {
    const { container } = render(
      <AnalysisDisplay analysis={analysis} apiUrl="http://x" onExport={() => {}} />,
    );
    const meta = container.querySelector('.metadata')?.textContent ?? '';
    expect(meta).toMatch(/tokens/);
    expect(meta).toContain('$0.0072');
  });
});
