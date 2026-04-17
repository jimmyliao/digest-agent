"""LeapCore Interface — Framework-Agnostic Agent Abstractions

Public ABC definitions for agents, orchestrators, tools, memory, and
pipelines.  These interfaces are intentionally free of any framework
dependency so that concrete implementations (in private repos) can bind
to Google ADK, Claude Agent SDK, Microsoft Agent Framework, or any
other runtime.

Usage::

    from leapcore_iface import AgentBase, ToolBase

    class MyTool(ToolBase):
        def execute(self, **kwargs):
            ...
"""

from .agent import AgentBase
from .memory import MEMORY_SCOPES, MemoryProviderBase
from .orchestrator import OrchestratorBase
from .pipeline import PipelineBase, PipelineStep
from .tool import ToolBase

__all__ = [
    "AgentBase",
    "MEMORY_SCOPES",
    "MemoryProviderBase",
    "OrchestratorBase",
    "PipelineBase",
    "PipelineStep",
    "ToolBase",
]
