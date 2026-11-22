import json
from dataclasses import asdict
from pathlib import Path

from nexus_core.config import NexusConfig


class ConfigManager:
    """Load, validate and persist NEXUS configuration."""

    def __init__(self, config_path=None):
        self.config_path = (
            Path(config_path)
            if config_path
            else Path(__file__).with_name("config.json")
        )

        self._config = NexusConfig()

    @property
    def config(self):
        return self._config

    def load(self):
        if not self.config_path.exists():
            self.save()
            return self._config

        try:
            data = json.loads(
                self.config_path.read_text(encoding="utf-8")
            )

            if not isinstance(data, dict):
                raise ValueError("Configuration must be a JSON object.")

            allowed = set(asdict(NexusConfig()).keys())

            if not set(data).issubset(allowed):
                raise ValueError("Unknown configuration fields.")

            self._config = NexusConfig(**data)
            return self._config

        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid NEXUS configuration: {error}"
            ) from error

    def save(self, config=None):
        config = config or self._config

        if not isinstance(config, NexusConfig):
            raise TypeError("Expected NexusConfig.")

        self.config_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        temporary_path = self.config_path.with_suffix(".tmp")

        temporary_path.write_text(
            json.dumps(
                asdict(config),
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        temporary_path.replace(self.config_path)
        self._config = config

        return True

    def update(self, **changes):
        current = asdict(self._config)

        unknown = set(changes) - set(current)

        if unknown:
            raise ValueError(
                f"Unknown configuration fields: {sorted(unknown)}"
            )

        current.update(changes)

        updated = NexusConfig(**current)
        self.save(updated)

        return updated

    def reset(self):
        self._config = NexusConfig()
        self.save()

        return self._config
