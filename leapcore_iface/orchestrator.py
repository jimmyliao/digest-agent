"""LeapCore Interface — OrchestratorBase ABC

Framework-agnostic abstract base class for multi-agent orchestration.
Maps to ADK's agent-transfer / sub_agents pattern, Claude's tool-based
delegation, and similar multi-agent runtimes.
"""

from abc import abstractmethod
from typing import Any, List, Optional

from .agent import AgentBase


class OrchestratorBase(AgentBase):
    """Abstract base for orchestrator (meta) agents.

    An orchestrator manages a set of sub-agents and delegates tasks to
    them according to a configurable strategy.

    Attributes:
        sub_agents: Child agents this orchestrator can delegate to.
        delegation_strategy: How delegation decisions are made.
            Common values: ``"llm_driven"``, ``"sequential"``,
            ``"parallel"``.
    """

    sub_agents: List[AgentBase]
    delegation_strategy: str

    def __init__(
        self,
        name: str,
        model: str,
        instruction: str,
        sub_agents: Optional[List[AgentBase]] = None,
        delegation_strategy: str = "llm_driven",
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, model=model, instruction=instruction, **kwargs)
        self.sub_agents = sub_agents or []
        self.delegation_strategy = delegation_strategy

    @abstractmethod
    def delegate(self, task: str, target_agent: str, **kwargs: Any) -> Any:
        """Delegate a task to a named sub-agent.

        Args:
            task: Description of the sub-task.
            target_agent: ``name`` attribute of the target sub-agent.
            **kwargs: Additional delegation context.

        Returns:
            Result from the sub-agent.

        Raises:
            ValueError: If *target_agent* is not found among sub_agents.
        """
        ...

    def get_agent(self, name: str) -> Optional[AgentBase]:
        """Look up a sub-agent by name.

        Returns:
            The matching :class:`AgentBase` or ``None``.
        """
        for agent in self.sub_agents:
            if agent.name == name:
                return agent
        return None

    def __repr__(self) -> str:
        agent_names = [a.name for a in self.sub_agents]
        return (
            f"{self.__class__.__name__}(name={self.name!r}, "
            f"strategy={self.delegation_strategy!r}, "
            f"sub_agents={agent_names})"
        )
