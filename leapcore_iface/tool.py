"""LeapCore Interface — ToolBase ABC

Framework-agnostic abstract base class for agent tools.
Implementations live in private repos and wrap framework-specific
tool APIs (Google ADK FunctionTool, Claude tool_use, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class ToolBase(ABC):
    """Abstract base for all agent tools.

    A tool encapsulates a single capability (API call, code execution,
    data retrieval, etc.) that an agent can invoke during reasoning.

    Attributes:
        name: Unique identifier used by the agent to select this tool.
        description: Human-readable description shown to the LLM so it
            can decide when to call this tool.
    """

    name: str
    description: str

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Execute the tool synchronously.

        Args:
            **kwargs: Tool-specific parameters.

        Returns:
            Tool execution result in an implementation-defined format.
        """
        ...

    @abstractmethod
    async def execute_async(self, **kwargs: Any) -> Any:
        """Execute the tool asynchronously.

        Args:
            **kwargs: Tool-specific parameters.

        Returns:
            Tool execution result in an implementation-defined format.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
