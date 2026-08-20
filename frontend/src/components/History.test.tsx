import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import History from './History';
import type { Analysis } from '../types';

function makeAnalysis(over: Partial<Analysis> = {}): Analysis {
  return {
    id: 'id-1',
    filename: 'cat.png',
    uploaded_at: '2026-08-20T10:00:00Z',
    description: 'a cat',
    objects: [],
    sentiment: 'happy',
    tags: ['animal', 'cat'],
    extracted_text: '',
    processing_time_ms: 10,
    input_tokens: 0,
    output_tokens: 0,
    cost_usd: 0,
    image_url: '/api/images/id-1',
    ...over,
  };
}

const noop = () => {};

describe('History', () => {
  it('shows the empty state when there are no images', () => {
    render(<History images={[]} apiUrl="http://x" onSelect={noop} onDelete={noop} />);
    expect(screen.getByText('No images analyzed yet.')).toBeInTheDocument();
  });

  it('renders the analyzed images', () => {
    render(
      <History
        images={[makeAnalysis()]}
        apiUrl="http://x"
        onSelect={noop}
        onDelete={noop}
      />,
    );
    expect(screen.getByText('cat.png')).toBeInTheDocument();
  });

  it('filters by the search query', async () => {
    const images = [
      makeAnalysis({ id: '1', filename: 'cat.png', tags: ['cat'] }),
      makeAnalysis({ id: '2', filename: 'dog.png', tags: ['dog'] }),
    ];
    render(
      <History images={images} apiUrl="http://x" onSelect={noop} onDelete={noop} />,
    );

    await userEvent.type(screen.getByPlaceholderText(/search/i), 'dog');
    expect(screen.getByText('dog.png')).toBeInTheDocument();
    expect(screen.queryByText('cat.png')).not.toBeInTheDocument();
  });

  it('calls onDelete (and not onSelect) when the delete button is clicked', async () => {
    const onDelete = vi.fn();
    const onSelect = vi.fn();
    render(
      <History
        images={[makeAnalysis({ id: 'id-42' })]}
        apiUrl="http://x"
        onSelect={onSelect}
        onDelete={onDelete}
      />,
    );

    await userEvent.click(screen.getByTitle('Delete this analysis'));
    expect(onDelete).toHaveBeenCalledWith('id-42');
    expect(onSelect).not.toHaveBeenCalled();
  });
});
