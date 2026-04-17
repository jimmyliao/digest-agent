/**
 * LeapCore Interface — TypeScript port of Python ABCs
 *
 * Framework-agnostic abstract classes for AI agents.
 * Designed to map cleanly onto Google ADK TypeScript, Anthropic Claude Agent SDK,
 * Microsoft Semantic Kernel, and similar runtimes.
 */

// ---------------------------------------------------------------------------
// ToolBase
// ---------------------------------------------------------------------------

/**
 * Abstract base for all agent tools.
 *
 * A tool encapsulates a single capability (API call, code execution,
 * data retrieval, etc.) that an agent can invoke during reasoning.
 */
export abstract class ToolBase {
  /** Unique identifier used by the agent to select this tool. */
  name: string;
  /** Human-readable description shown to the LLM so it can decide when to call this tool. */
  description: string;

  constructor(name: string, description: string) {
    this.name = name;
    this.description = description;
  }

  /**
   * Execute the tool synchronously.
   * @param kwargs Tool-specific parameters.
   * @returns Tool execution result in an implementation-defined format.
   */
  abstract execute(kwargs: Record<string, unknown>): unknown;

  /**
   * Execute the tool asynchronously.
   * @param kwargs Tool-specific parameters.
   * @returns Tool execution result in an implementation-defined format.
   */
  abstract executeAsync(kwargs: Record<string, unknown>): Promise<unknown>;

  toString(): string {
    return `${this.constructor.name}(name=${JSON.stringify(this.name)})`;
  }
}

// ---------------------------------------------------------------------------
// AgentBase
// ---------------------------------------------------------------------------

/**
 * Abstract base for all agents.
 *
 * An agent wraps an LLM with an instruction prompt, a set of tools,
 * and a run interface. Concrete implementations bind to a specific
 * framework (ADK, Claude, etc.) without changing the public API.
 */
export abstract class AgentBase {
  /** Unique agent identifier. */
  name: string;
  /** LLM model name or endpoint (e.g. "gemini-2.0-flash"). */
  model: string;
  /** System prompt / persona that guides agent behaviour. */
  instruction: string;
  /** Tools the agent is allowed to invoke. */
  tools: ToolBase[];

  constructor(
    name: string,
    model: string,
    instruction: string,
    tools: ToolBase[] = [],
  ) {
    this.name = name;
    this.model = model;
    this.instruction = instruction;
    this.tools = tools;
  }

  /**
   * Run the agent synchronously.
   * @param input User message or task description.
   * @param options Framework-specific options (session id, context, etc.).
   * @returns Agent response in an implementation-defined format.
   */
  abstract run(input: string, options?: Record<string, unknown>): unknown;

  /**
   * Run the agent asynchronously.
   * @param input User message or task description.
   * @param options Framework-specific options.
   * @returns Agent response in an implementation-defined format.
   */
  abstract runAsync(input: string, options?: Record<string, unknown>): Promise<unknown>;

  toString(): string {
    return `${this.constructor.name}(name=${JSON.stringify(this.name)}, model=${JSON.stringify(this.model)})`;
  }
}

// ---------------------------------------------------------------------------
// OrchestratorBase
// ---------------------------------------------------------------------------

/**
 * Abstract base for orchestrator (meta) agents.
 *
 * An orchestrator manages a set of sub-agents and delegates tasks to
 * them according to a configurable strategy.
 */
export abstract class OrchestratorBase extends AgentBase {
  /** Child agents this orchestrator can delegate to. */
  subAgents: AgentBase[];
  /**
   * How delegation decisions are made.
   * Common values: "llm_driven", "sequential", "parallel".
   */
  delegationStrategy: string;

  constructor(
    name: string,
    model: string,
    instruction: string,
    subAgents: AgentBase[] = [],
    delegationStrategy: string = 'llm_driven',
    tools: ToolBase[] = [],
  ) {
    super(name, model, instruction, tools);
    this.subAgents = subAgents;
    this.delegationStrategy = delegationStrategy;
  }

  /**
   * Delegate a task to a named sub-agent.
   * @param task Description of the sub-task.
   * @param targetAgent `name` attribute of the target sub-agent.
   * @param options Additional delegation context.
   * @returns Result from the sub-agent.
   * @throws {Error} If targetAgent is not found among subAgents.
   */
  abstract delegate(
    task: string,
    targetAgent: string,
    options?: Record<string, unknown>,
  ): unknown;

  /**
   * Look up a sub-agent by name.
   * @returns The matching AgentBase or undefined.
   */
  getAgent(name: string): AgentBase | undefined {
    return this.subAgents.find((agent) => agent.name === name);
  }

  toString(): string {
    const agentNames = this.subAgents.map((a) => a.name);
    return (
      `${this.constructor.name}(name=${JSON.stringify(this.name)}, ` +
      `strategy=${JSON.stringify(this.delegationStrategy)}, ` +
      `subAgents=${JSON.stringify(agentNames)})`
    );
  }
}

// ---------------------------------------------------------------------------
// PipelineBase
// ---------------------------------------------------------------------------

/**
 * A pipeline step is either an agent or any callable.
 */
export type PipelineStep = AgentBase | ((...args: unknown[]) => unknown);

/**
 * Abstract base for agent execution pipelines.
 *
 * A pipeline composes multiple steps — agents or plain callables —
 * into a higher-level workflow. The `mode` attribute controls the
 * execution strategy.
 */
export abstract class PipelineBase {
  /** Ordered list of pipeline steps. */
  steps: PipelineStep[];
  /**
   * Execution strategy.
   * - "sequential" — run steps one after another, passing each output as the next input.
   * - "parallel"   — run all steps concurrently and aggregate.
   * - "conditional" — evaluate a condition to pick the next step (implementation-specific).
   */
  mode: 'sequential' | 'parallel' | 'conditional';

  constructor(
    steps: PipelineStep[] = [],
    mode: 'sequential' | 'parallel' | 'conditional' = 'sequential',
  ) {
    this.steps = steps;
    this.mode = mode;
  }

  /**
   * Execute the pipeline synchronously.
   * @param input Initial input fed to the first step.
   * @param options Pipeline-level options.
   * @returns Final output after all steps complete.
   */
  abstract run(input: unknown, options?: Record<string, unknown>): unknown;

  /**
   * Execute the pipeline asynchronously.
   * @param input Initial input fed to the first step.
   * @param options Pipeline-level options.
   * @returns Final output after all steps complete.
   */
  abstract runAsync(input: unknown, options?: Record<string, unknown>): Promise<unknown>;

  /** Append a step to the pipeline. */
  addStep(step: PipelineStep): void {
    this.steps.push(step);
  }

  toString(): string {
    return `${this.constructor.name}(mode=${JSON.stringify(this.mode)}, steps=${this.steps.length})`;
  }
}

// ---------------------------------------------------------------------------
// MemoryProviderBase
// ---------------------------------------------------------------------------

/**
 * Recognised memory scopes, ordered by lifetime:
 * - "temp"    — discarded after a single turn / tool call.
 * - "session" — persists for the current conversation session.
 * - "user"    — persists across sessions for a given user.
 * - "app"     — shared across all users of the application.
 */
export const MEMORY_SCOPES = ['temp', 'session', 'user', 'app'] as const;
export type MemoryScope = (typeof MEMORY_SCOPES)[number];

/**
 * Abstract base for agent memory providers.
 *
 * Memory is organised into scopes with increasing lifetime.
 * Implementations may back these scopes with in-memory maps, Redis,
 * vector stores, or any other storage engine.
 */
export abstract class MemoryProviderBase {
  /**
   * Store a value under `key` in the given `scope`.
   * @param key Identifier for the memory entry.
   * @param value Arbitrary data to store.
   * @param scope One of "temp", "session", "user", "app".
   */
  abstract add(key: string, value: unknown, scope?: MemoryScope): void;

  /**
   * Retrieve a value by exact `key`.
   * @param key Identifier for the memory entry.
   * @param scope Scope to search in.
   * @returns The stored value, or undefined if not found.
   */
  abstract get(key: string, scope?: MemoryScope): unknown | undefined;

  /**
   * Semantic or keyword search over memory entries.
   * @param query Search query (may be semantic depending on impl).
   * @param scope Scope to search in.
   * @param limit Maximum number of results.
   * @returns List of records with at least `key` and `value` fields.
   */
  abstract search(
    query: string,
    scope?: MemoryScope,
    limit?: number,
  ): Array<{ key: string; value: unknown; [extra: string]: unknown }>;

  /**
   * Remove all entries in the given `scope`.
   * @param scope Scope to clear.
   */
  abstract clear(scope?: MemoryScope): void;

  toString(): string {
    return `${this.constructor.name}()`;
  }
}
