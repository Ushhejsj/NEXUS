from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NexusConfig:
    """Central configuration for the NEXUS Core."""

    app_name: str = "CORE NEXUS"

    provider: str = "ollama"
    model: str = "gemma3:4b"
    base_url: str = "http://127.0.0.1:11434"

    request_timeout: float = 60.0
    context_messages: int = 16

    def __post_init__(self):
        if not self.app_name.strip():
            raise ValueError("Application name cannot be empty.")

        if not self.provider.strip():
            raise ValueError("AI provider cannot be empty.")

        if not self.model.strip():
            raise ValueError("AI model cannot be empty.")

        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("Invalid AI server URL.")

        if not 1 <= self.request_timeout <= 300:
            raise ValueError("Request timeout must be between 1 and 300.")

        if not 1 <= self.context_messages <= 100:
            raise ValueError("Context size must be between 1 and 100.")
