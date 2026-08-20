import { expect, test } from '@playwright/test';

const analysis = {
  id: 'e1',
  filename: 't.png',
  uploaded_at: '2026-08-20T10:00:00Z',
  description: 'A blue circle.',
  objects: [{ name: 'circle', confidence: 0.95 }],
  sentiment: 'neutral',
  tags: ['blue', 'circle'],
  extracted_text: '',
  processing_time_ms: 10,
  input_tokens: 80,
  output_tokens: 40,
  cost_usd: 0.0008,
  image_url: '/api/images/e1',
};

// 1x1 transparent PNG.
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC',
  'base64',
);

test.beforeEach(async ({ page }) => {
  // Mock the backend so the E2E is deterministic and needs no API key.
  await page.route('**/api/history', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
  );
  await page.route('**/api/metrics', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_analyses: 3,
        total_input_tokens: 2000,
        total_output_tokens: 800,
        total_cost_usd: 0.02,
        avg_processing_time_ms: 4000,
        model: 'claude-sonnet-5',
        by_day: [{ day: '2026-08-20', count: 3, cost_usd: 0.02 }],
      }),
    }),
  );
  await page.route('**/api/images/**', (route) =>
    route.fulfill({ status: 200, contentType: 'image/png', body: PNG }),
  );
  await page.route('**/api/analyze/stream*', (route) => {
    const sse =
      [
        'data: {"type":"start","id":"e1","filename":"t.png","image_url":"/api/images/e1"}',
        'data: {"type":"delta","text":"A blue "}',
        'data: {"type":"delta","text":"circle."}',
        `data: {"type":"complete","analysis":${JSON.stringify(analysis)}}`,
      ].join('\n\n') + '\n\n';
    route.fulfill({ status: 200, contentType: 'text/event-stream', body: sse });
  });
});

test('loads, toggles theme, and analyzes an image', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Image Analyzer/ })).toBeVisible();

  // Theme toggle flips the document theme.
  const before = await page.evaluate(() => document.documentElement.dataset.theme);
  await page.getByRole('button', { name: 'Toggle theme' }).click();
  const after = await page.evaluate(() => document.documentElement.dataset.theme);
  expect(after).not.toBe(before);

  // Upload -> SSE stream -> analysis renders.
  await page.setInputFiles('input[type="file"]', {
    name: 't.png',
    mimeType: 'image/png',
    buffer: PNG,
  });

  await expect(page.getByText('A blue circle.')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('heading', { name: 't.png' })).toBeVisible();

  // Dashboard tab shows the usage metrics.
  await page.getByRole('button', { name: 'Dashboard' }).click();
  await expect(page.getByText('Analyses', { exact: true })).toBeVisible();
  await expect(page.getByText('claude-sonnet-5')).toBeVisible();
});
