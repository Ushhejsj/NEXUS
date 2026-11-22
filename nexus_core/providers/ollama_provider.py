import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .base import BaseAIProvider


class ProviderError(Exception):
    """Raised when an AI provider request fails."""


class OllamaProvider(BaseAIProvider):
    """Communication layer for the local Ollama API."""

    def __init__(self, config):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.model = config.model
        self.timeout = config.request_timeout

    def _request(self, endpoint, method="GET", payload=None):
        url = f"{self.base_url}{endpoint}"

        data = None
        headers = {}

        if payload is not None:
            data = json.dumps(
                payload,
                ensure_ascii=False
            ).encode("utf-8")

            headers["Content-Type"] = "application/json"

        request = Request(
            url,
            data=data,
            headers=headers,
            method=method
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw)

        except HTTPError as error:
            details = error.read().decode(
                "utf-8",
                errors="replace"
            )[:1000]

            raise ProviderError(
                f"Ollama HTTP error {error.code}: {details}"
            ) from error

        except (URLError, TimeoutError, OSError) as error:
            raise ProviderError(
                f"Cannot connect to Ollama: {error}"
            ) from error

        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ProviderError(
                "Ollama returned invalid JSON or text."
            ) from error

    def check_connection(self):
        """Check Ollama availability and model installation."""

        result = self._request("/api/tags")

        models = result.get("models", [])

        available = [
            item.get("name", "")
            for item in models
        ]

        model_found = any(
            name == self.model or name.startswith(self.model + ":")
            for name in available
        )

        return {
            "connected": True,
            "model": self.model,
            "model_available": model_found,
            "available_models": available
        }

    def chat(self, messages, temperature=0.2):
        """Send a conversation to Ollama and return its response."""

        if not isinstance(messages, list) or not messages:
            raise ValueError("Messages must be a non-empty list.")

        if not isinstance(temperature, (int, float)):
            raise ValueError("Temperature must be numeric.")

        if not 0 <= temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2.")

        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("Each message must be a dictionary.")

            if message.get("role") not in (
                "system", "user", "assistant", "tool"
            ):
                raise ValueError("Invalid message role.")

            if not isinstance(message.get("content"), str):
                raise ValueError("Message content must be text.")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        result = self._request(
            "/api/chat",
            method="POST",
            payload=payload
        )

        message = result.get("message")

        if not isinstance(message, dict):
            raise ProviderError("Ollama response has no message.")

        content = message.get("content")

        if not isinstance(content, str):
            raise ProviderError("Ollama response has invalid content.")

        return content
