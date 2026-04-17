"""LeapCore Interface — AgentBase ABC

Framework-agnostic abstract base class for AI agents.
Designed to map cleanly onto Google ADK Agent, Claude Agent SDK,
Microsoft Agent Framework, and similar runtimes.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from .tool import ToolBase


class AgentBase(ABC):
    """Abstract base for all agents.

    An agent wraps an LLM with an instruction prompt, a set of tools,
    and a run interface.  Concrete implementations bind to a specific
    framework (ADK, Claude, etc.) without changing the public API.

    Attributes:
        name: Unique agent identifier.
        model: LLM model name or endpoint (e.g. ``"gemini-2.0-flash"``).
        instruction: System prompt / persona that guides agent behaviour.
        tools: Tools the agent is allowed to invoke.
    """

    name: str
    model: str
    instruction: str
    tools: List[ToolBase]

    def __init__(
        self,
        name: str,
        model: str,
        instruction: str,
        tools: Optional[List[ToolBase]] = None,
    ) -> None:
        self.name = name
        self.model = model
        self.instruction = instruction
        self.tools = tools or []

    @abstractmethod
    def run(self, input: str, **kwargs: Any) -> Any:
        """Run the agent synchronously.

        Args:
            input: User message or task description.
            **kwargs: Framework-specific options (session id, context, etc.).

        Returns:
            Agent response in an implementation-defined format.
        """
        ...

    @abstractmethod
    async def run_async(self, input: str, **kwargs: Any) -> Any:
        """Run the agent asynchronously.

        Args:
            input: User message or task description.
            **kwargs: Framework-specific options.

        Returns:
            Agent response in an implementation-defined format.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, model={self.model!r})"
