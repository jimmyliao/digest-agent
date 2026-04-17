import type { AgentBase, OrchestratorBase, ToolBase } from '@leapcore/iface';

// Stub — full ADK TypeScript orchestrator implementation pending @google/adk TypeScript SDK release
export class DigestOrchestrator implements OrchestratorBase {
  name: string;
  model: string;
  instruction: string;
  tools: ToolBase[];
  subAgents: AgentBase[];
  delegationStrategy: string;

  constructor(subAgents: AgentBase[] = [], model = 'gemini-2.5-flash-preview-04-17') {
    this.name = 'digest-orchestrator';
    this.model = model;
    this.instruction = 'Orchestrate the digest pipeline: fetch, summarize, publish.';
    this.tools = [];
    this.subAgents = subAgents;
    this.delegationStrategy = 'llm_driven';
  }

  run(input: string): string {
    throw new Error('Use runAsync for LLM operations');
  }

  async runAsync(input: string): Promise<string> {
    throw new Error('Not implemented — awaiting ADK TypeScript GA');
  }

  delegate(task: string, targetAgent: string): unknown {
    const agent = this.getAgent(targetAgent);
    if (!agent) {
      throw new Error(`Agent not found: ${targetAgent}`);
    }
    return agent.run(task);
  }

  getAgent(name: string): AgentBase | undefined {
    return this.subAgents.find((a) => a.name === name);
  }
}
