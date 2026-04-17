import type { AgentBase, ToolBase } from '@leapcore/iface';

// Stub — full ADK TypeScript implementation pending @google/adk TypeScript SDK release
export class SummarizerAgent implements AgentBase {
  name: string;
  model: string;
  instruction: string;
  tools: ToolBase[];

  constructor(model = 'gemini-2.5-flash-preview-04-17') {
    this.name = 'summarizer';
    this.model = model;
    this.instruction = 'Summarize news articles concisely in Traditional Chinese.';
    this.tools = [];
  }

  run(input: string): string {
    throw new Error('Use runAsync for LLM operations');
  }

  async runAsync(input: string): Promise<string> {
    // TODO: wire to @google/adk Agent once TypeScript SDK is stable
    throw new Error('Not implemented — awaiting ADK TypeScript GA');
  }
}
