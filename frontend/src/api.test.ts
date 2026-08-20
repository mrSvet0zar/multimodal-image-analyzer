import { afterEach, describe, expect, it, vi } from 'vitest';
import { analyzeStream, analyzeVideo, deleteAnalysis, fetchHistory } from './api';
import type { Analysis } from './types';

const sampleAnalysis: Analysis = {
  id: 'abc',
  filename: 'a.png',
  uploaded_at: '2026-08-20T10:00:00Z',
  description: 'a red square',
  objects: [{ name: 'square', confidence: 0.9 }],
  sentiment: 'neutral',
  tags: ['red'],
  extracted_text: '',
  processing_time_ms: 12,
  input_tokens: 80,
  output_tokens: 40,
  cost_usd: 0.0008,
  image_url: '/api/images/abc',
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe('fetchHistory', () => {
  it('returns the parsed list', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify([sampleAnalysis]))),
    );
    const history = await fetchHistory();
    expect(history).toHaveLength(1);
    expect(history[0].id).toBe('abc');
  });
});

describe('deleteAnalysis', () => {
  it('throws on a non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })));
    await expect(deleteAnalysis('abc')).rejects.toThrow('Error: 500');
  });
});

describe('analyzeVideo', () => {
  it('posts the file and returns the analysis', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(sampleAnalysis)));
    vi.stubGlobal('fetch', fetchMock);

    const file = new File([new Uint8Array([1, 2, 3])], 'clip.mp4', {
      type: 'video/mp4',
    });
    const result = await analyzeVideo(file, 'medium', 'en');

    expect(result.id).toBe('abc');
    expect(fetchMock.mock.calls[0][0]).toContain('/api/analyze/video');
  });
});

describe('analyzeStream', () => {
  it('emits deltas then complete, without leaking the marker/JSON', async () => {
    const sse =
      [
        'data: {"type":"start","id":"1","filename":"a.png","image_url":"/api/images/1"}',
        'data: {"type":"delta","text":"A red "}',
        'data: {"type":"delta","text":"square."}',
        `data: {"type":"complete","analysis":${JSON.stringify(sampleAnalysis)}}`,
      ].join('\n\n') + '\n\n';

    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(sse));
        controller.close();
      },
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(body, {
          status: 200,
          headers: { 'content-type': 'text/event-stream' },
        }),
      ),
    );

    const deltas: string[] = [];
    const completions: Analysis[] = [];
    const file = new File([new Uint8Array([1, 2, 3])], 'a.png', { type: 'image/png' });

    await analyzeStream(file, 'medium', 'en', {
      onDelta: (t) => deltas.push(t),
      onComplete: (a) => completions.push(a),
    });

    expect(deltas.join('')).toBe('A red square.');
    expect(completions).toHaveLength(1);
    expect(completions[0].id).toBe('abc');
  });

  it('throws on a non-ok response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'boom' }), { status: 400 }),
      ),
    );
    const file = new File([new Uint8Array([1])], 'a.png', { type: 'image/png' });
    await expect(
      analyzeStream(file, 'medium', 'en', { onDelta: () => {}, onComplete: () => {} }),
    ).rejects.toThrow('boom');
  });
});
