from abc import ABC, abstractmethod
from enum import Enum


class ModuleStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class NexusModule(ABC):
    """Base interface for CORE NEXUS modules."""

    name: str = ""
    version: str = "1.0.0"
    description: str = ""

    def __init__(self):
        self._status = ModuleStatus.STOPPED
        self._last_error = ""

    @abstractmethod
    def start(self):
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        raise NotImplementedError

    @property
    def status(self):
        return self._status

    @property
    def is_running(self):
        return self._status == ModuleStatus.RUNNING

    @property
    def last_error(self):
        return self._last_error
