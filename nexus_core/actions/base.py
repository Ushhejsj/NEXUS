from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionResult:
    success: bool
    action: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "success": self.success,
            "action": self.action,
            "message": self.message,
            "data": self.data
        }


class BaseAction(ABC):
    """Base interface for all NEXUS actions."""

    name: str = ""
    description: str = ""
    required_permissions: tuple[str, ...] = ()

    @abstractmethod
    def validate(self, parameters: dict[str, Any]) -> bool:
        """Validate action parameters."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, parameters: dict[str, Any]) -> ActionResult:
        """Execute the action."""
        raise NotImplementedError
