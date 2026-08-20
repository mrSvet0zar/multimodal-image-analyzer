import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// RTL auto-cleanup only runs with `globals: true`; register it explicitly.
afterEach(() => {
  cleanup();
});
