import type { NextConfig } from 'next';
const config: NextConfig = {
  output: 'standalone',
  env: { LLM_PROVIDER: process.env.LLM_PROVIDER ?? 'gemini' },
};
export default config;
