import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  resolve: {
    alias: {
      // Mirror the "@/*" path mapping from tsconfig.json so route handlers
      // (which import via "@/lib/db") are resolvable inside vitest.
      '@': path.resolve(__dirname, '.'),
    },
  },
  test: {
    environment: 'node',
    globals: true,
    testTimeout: 10000,
  },
});
