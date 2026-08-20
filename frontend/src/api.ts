import type {
  Analysis,
  BatchResult,
  DetailLevel,
  ExportFormat,
  Metrics,
} from './types';

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail || `Error: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function fetchHistory(): Promise<Analysis[]> {
  return fetch(`${API_URL}/api/history`).then((r) => jsonOrThrow<Analysis[]>(r));
}

export function fetchMetrics(): Promise<Metrics> {
  return fetch(`${API_URL}/api/metrics`).then((r) => jsonOrThrow<Metrics>(r));
}

export function analyzeBatch(
  files: File[],
  detailLevel: DetailLevel,
  language: string,
): Promise<BatchResult> {
  const fd = new FormData();
  files.forEach((f) => fd.append('files', f));
  return fetch(
    `${API_URL}/api/analyze/batch?detail_level=${detailLevel}&language=${language}`,
    { method: 'POST', body: fd },
  ).then((r) => jsonOrThrow<BatchResult>(r));
}

export function analyzeVideo(
  file: File,
  detailLevel: DetailLevel,
  language: string,
): Promise<Analysis> {
  const fd = new FormData();
  fd.append('file', file);
  return fetch(
    `${API_URL}/api/analyze/video?detail_level=${detailLevel}&language=${language}`,
    { method: 'POST', body: fd },
  ).then((r) => jsonOrThrow<Analysis>(r));
}

export async function deleteAnalysis(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/analysis/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Error: ${res.status}`);
}

export async function exportAnalysis(
  id: string,
  format: ExportFormat,
): Promise<{ markdown?: string } & Record<string, unknown>> {
  const res = await fetch(`${API_URL}/api/export/${id}?format=${format}`);
  return jsonOrThrow(res);
}

export interface StreamHandlers {
  onStart?: (e: { id: string; filename: string; image_url: string }) => void;
  onDelta: (text: string) => void;
  onComplete: (analysis: Analysis) => void;
}

type StreamEvent =
  | { type: 'start'; id: string; filename: string; image_url: string }
  | { type: 'delta'; text: string }
  | { type: 'complete'; analysis: Analysis }
  | { type: 'error'; detail: string };

/** POST an image and consume the SSE stream via callbacks. */
export async function analyzeStream(
  file: File,
  detailLevel: DetailLevel,
  language: string,
  handlers: StreamHandlers,
): Promise<void> {
  const fd = new FormData();
  fd.append('file', file);

  const res = await fetch(
    `${API_URL}/api/analyze/stream?detail_level=${detailLevel}&language=${language}`,
    { method: 'POST', body: fd },
  );
  if (!res.ok || !res.body) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail || `Error: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() ?? '';
    for (const block of blocks) {
      const line = block.split('\n').find((l) => l.startsWith('data:'));
      if (!line) continue;
      const evt = JSON.parse(line.slice(5).trim()) as StreamEvent;
      if (evt.type === 'delta') handlers.onDelta(evt.text);
      else if (evt.type === 'complete') handlers.onComplete(evt.analysis);
      else if (evt.type === 'start') handlers.onStart?.(evt);
      else if (evt.type === 'error') throw new Error(evt.detail);
    }
  }
}
