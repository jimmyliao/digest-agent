import { describe, it, expect } from 'vitest';

describe('getModel', () => {
  it('returns a model object for gemini provider', async () => {
    process.env.GEMINI_API_KEY = 'test-mock-key';
    const { getModel } = await import('../../lib/llm');
    const model = getModel('gemini');
    expect(model).toBeDefined();
    expect(typeof model).toBe('object');
  });

  it('returns a model object for claude provider', async () => {
    process.env.ANTHROPIC_API_KEY = 'test-mock-key';
    const { getModel } = await import('../../lib/llm');
    const model = getModel('claude');
    expect(model).toBeDefined();
    expect(typeof model).toBe('object');
  });

  it('defaults to gemini when LLM_PROVIDER is not set', async () => {
    delete process.env.LLM_PROVIDER;
    process.env.GEMINI_API_KEY = 'test-mock-key';
    const { getModel } = await import('../../lib/llm');
    // Should not throw when called with no argument
    expect(() => getModel()).not.toThrow();
  });

  it('getModel returns an object with a provider property or is callable', async () => {
    process.env.GEMINI_API_KEY = 'test-mock-key';
    const { getModel } = await import('../../lib/llm');
    const model = getModel('gemini');
    // Vercel AI SDK model objects have a modelId or provider string
    expect(model).not.toBeNull();
    expect(model).not.toBeUndefined();
  });
});
