from collections import defaultdict
from threading import RLock

from nexus_core.events.event import NexusEvent


class EventBus:
    """Central event dispatcher for CORE NEXUS."""

    def __init__(self):
        self._subscribers = defaultdict(list)
        self._lock = RLock()
        self._event_count = 0

    def subscribe(self, event_name, callback):
        if not isinstance(event_name, str) or not event_name.strip():
            raise ValueError("Event name cannot be empty.")

        if not callable(callback):
            raise TypeError("Callback must be callable.")

        with self._lock:
            if callback not in self._subscribers[event_name]:
                self._subscribers[event_name].append(callback)

        return True

    def unsubscribe(self, event_name, callback):
        with self._lock:
            callbacks = self._subscribers.get(event_name, [])

            if callback not in callbacks:
                return False

            callbacks.remove(callback)

            if not callbacks:
                self._subscribers.pop(event_name, None)

            return True

    def publish(self, event):
        if not isinstance(event, NexusEvent):
            raise TypeError("Expected a NexusEvent instance.")

        with self._lock:
            callbacks = list(
                self._subscribers.get(event.name, [])
            )
            self._event_count += 1

        results = []

        for callback in callbacks:
            try:
                callback(event)
                results.append({
                    "success": True,
                    "callback": getattr(
                        callback, "__name__", "anonymous"
                    )
                })
            except Exception as error:
                results.append({
                    "success": False,
                    "callback": getattr(
                        callback, "__name__", "anonymous"
                    ),
                    "error": type(error).__name__
                })

        return {
            "event_id": event.event_id,
            "event": event.name,
            "subscribers": len(callbacks),
            "results": results
        }

    def subscriber_count(self, event_name):
        with self._lock:
            return len(self._subscribers.get(event_name, []))

    @property
    def event_count(self):
        with self._lock:
            return self._event_count

    def clear(self):
        with self._lock:
            self._subscribers.clear()
