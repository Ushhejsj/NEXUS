from abc import ABC, abstractmethod


class BaseAIProvider(ABC):
    """Common interface for all NEXUS AI providers."""

    @abstractmethod
    def check_connection(self) -> dict:
        """Check provider availability."""
        raise NotImplementedError

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2
    ) -> str:
        """Send messages and return the AI response."""
        raise NotImplementedError
