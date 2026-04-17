"""LeapCore Interface — MemoryProviderBase ABC

Framework-agnostic abstract base class for agent memory / state.
Covers the spectrum from ephemeral session state to persistent user
knowledge, mapping to ADK's ``State`` prefix scopes, Claude's
conversation memory, and similar patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


# Recognised memory scopes, ordered by lifetime.
MEMORY_SCOPES = ("temp", "session", "user", "app")


class MemoryProviderBase(ABC):
    """Abstract base for agent memory providers.

    Memory is organised into *scopes* with increasing lifetime:

    * ``"temp"``    — discarded after a single turn / tool call.
    * ``"session"`` — persists for the current conversation session.
    * ``"user"``    — persists across sessions for a given user.
    * ``"app"``     — shared across all users of the application.

    Implementations may back these scopes with in-memory dicts, Redis,
    vector stores, or any other storage engine.
    """

    @abstractmethod
    def add(self, key: str, value: Any, scope: str = "session") -> None:
        """Store a value under *key* in the given *scope*.

        Args:
            key: Identifier for the memory entry.
            value: Arbitrary data to store.
            scope: One of ``"temp"``, ``"session"``, ``"user"``, ``"app"``.
        """
        ...

    @abstractmethod
    def get(self, key: str, scope: str = "session") -> Optional[Any]:
        """Retrieve a value by exact *key*.

        Args:
            key: Identifier for the memory entry.
            scope: Scope to search in.

        Returns:
            The stored value, or ``None`` if not found.
        """
        ...

    @abstractmethod
    def search(
        self, query: str, scope: str = "session", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Semantic or keyword search over memory entries.

        Args:
            query: Search query (may be semantic depending on impl).
            scope: Scope to search in.
            limit: Maximum number of results.

        Returns:
            List of dicts with at least ``"key"`` and ``"value"`` fields.
        """
        ...

    @abstractmethod
    def clear(self, scope: str = "session") -> None:
        """Remove all entries in the given *scope*.

        Args:
            scope: Scope to clear.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
