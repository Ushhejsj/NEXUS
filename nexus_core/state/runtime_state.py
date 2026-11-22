from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from threading import RLock


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class NexusState:
    status: str = "initializing"
    provider: str = "unknown"
    model: str = "unknown"
    started_at: str = ""
    last_activity: str = ""
    last_error: str = ""
    events_processed: int = 0


class RuntimeState:
    """Thread-safe runtime state manager for CORE NEXUS."""

    def __init__(self, provider="unknown", model="unknown"):
        self._lock = RLock()

        now = utc_now()

        self._state = NexusState(
            status="running",
            provider=provider,
            model=model,
            started_at=now,
            last_activity=now
        )

    def get_snapshot(self):
        with self._lock:
            return asdict(self._state)

    def update_activity(self):
        with self._lock:
            self._state.last_activity = utc_now()

    def set_status(self, status):
        allowed = {
            "initializing",
            "running",
            "idle",
            "error",
            "stopped"
        }

        if status not in allowed:
            raise ValueError("Invalid runtime status.")

        with self._lock:
            self._state.status = status
            self._state.last_activity = utc_now()

    def set_error(self, error):
        if not isinstance(error, str):
            raise TypeError("Error must be a string.")

        with self._lock:
            self._state.last_error = error
            self._state.status = "error"
            self._state.last_activity = utc_now()

    def clear_error(self):
        with self._lock:
            self._state.last_error = ""

            if self._state.status == "error":
                self._state.status = "running"

    def record_event(self):
        with self._lock:
            self._state.events_processed += 1
            self._state.last_activity = utc_now()

    def set_provider(self, provider, model):
        if not isinstance(provider, str) or not provider.strip():
            raise ValueError("Provider cannot be empty.")

        if not isinstance(model, str) or not model.strip():
            raise ValueError("Model cannot be empty.")

        with self._lock:
            self._state.provider = provider
            self._state.model = model
            self._state.last_activity = utc_now()
