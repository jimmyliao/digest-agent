"""LeapCore Interface — PipelineBase ABC

Framework-agnostic abstract base class for multi-step agent pipelines.
A pipeline chains agents and/or callable steps in a defined execution
order (sequential, parallel, or conditional).
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional, Union

from .agent import AgentBase


# A pipeline step is either an agent or any callable.
PipelineStep = Union[AgentBase, Callable[..., Any]]


class PipelineBase(ABC):
    """Abstract base for agent execution pipelines.

    A pipeline composes multiple steps — agents or plain callables —
    into a higher-level workflow.  The *mode* attribute controls the
    execution strategy.

    Attributes:
        steps: Ordered list of pipeline steps.
        mode: Execution strategy.  Common values:
            ``"sequential"`` — run steps one after another, passing
            each output as the next input.
            ``"parallel"`` — run all steps concurrently and aggregate.
            ``"conditional"`` — evaluate a condition to pick the next
            step (implementation-specific).
    """

    steps: List[PipelineStep]
    mode: str

    def __init__(
        self,
        steps: Optional[List[PipelineStep]] = None,
        mode: str = "sequential",
    ) -> None:
        self.steps = steps or []
        self.mode = mode

    @abstractmethod
    def run(self, input: Any, **kwargs: Any) -> Any:
        """Execute the pipeline synchronously.

        Args:
            input: Initial input fed to the first step.
            **kwargs: Pipeline-level options.

        Returns:
            Final output after all steps complete.
        """
        ...

    @abstractmethod
    async def run_async(self, input: Any, **kwargs: Any) -> Any:
        """Execute the pipeline asynchronously.

        Args:
            input: Initial input fed to the first step.
            **kwargs: Pipeline-level options.

        Returns:
            Final output after all steps complete.
        """
        ...

    def add_step(self, step: PipelineStep) -> None:
        """Append a step to the pipeline."""
        self.steps.append(step)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(mode={self.mode!r}, "
            f"steps={len(self.steps)})"
        )
