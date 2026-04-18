import type { NextConfig } from 'next';

/**
 * bun:sqlite  — Bun built-in, not available in Node/webpack
 * better-sqlite3 — native addon, must stay external so webpack skips bundling
 *
 * serverExternalPackages tells Next.js to leave these as require() calls
 * at runtime instead of bundling them through webpack.
 */
const config: NextConfig = {
  output: 'standalone',
  env: { LLM_PROVIDER: process.env.LLM_PROVIDER ?? 'gemini' },
  serverExternalPackages: ['better-sqlite3', 'bun:sqlite'],
};
export default config;
