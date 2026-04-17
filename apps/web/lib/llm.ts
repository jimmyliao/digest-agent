import { createGoogleGenerativeAI } from '@ai-sdk/google';
import { createAnthropic } from '@ai-sdk/anthropic';
import { generateText } from 'ai';

export type LLMProvider = 'gemini' | 'claude';

export function getModel(provider?: LLMProvider) {
  const p = provider ?? (process.env.LLM_PROVIDER as LLMProvider) ?? 'gemini';
  if (p === 'claude') {
    return createAnthropic()('claude-sonnet-4-6');
  }
  return createGoogleGenerativeAI()('gemini-2.5-flash-preview-04-17');
}

export async function summarizeArticle(
  title: string,
  content: string,
  provider?: LLMProvider
) {
  const model = getModel(provider);
  const { text } = await generateText({
    model,
    system: 'You are a news digest assistant. Summarize articles concisely in Traditional Chinese (繁體中文).',
    prompt: `Title: ${title}\n\nContent: ${content}\n\nProvide a 3-sentence summary.`,
  });
  return text;
}
