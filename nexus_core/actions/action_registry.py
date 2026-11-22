from nexus_core.actions.base import BaseAction, ActionResult
from nexus_core.actions.permission_manager import PermissionManager


class ActionRegistry:
    """Central registry and permission-controlled action dispatcher."""

    def __init__(self, permission_manager=None):
        self._actions: dict[str, BaseAction] = {}
        self.permissions = permission_manager or PermissionManager()

    def register(self, action: BaseAction):
        if not isinstance(action, BaseAction):
            raise TypeError("Action must inherit BaseAction.")

        name = action.name.strip().lower()

        if not name:
            raise ValueError("Action name cannot be empty.")

        if name in self._actions:
            raise ValueError(f"Action already registered: {name}")

        self._actions[name] = action
        return True

    def unregister(self, name: str):
        return self._actions.pop(name.strip().lower(), None) is not None

    def get(self, name: str):
        return self._actions.get(name.strip().lower())

    def list_actions(self):
        return [
            {
                "name": action.name,
                "description": action.description,
                "required_permissions": list(
                    action.required_permissions
                )
            }
            for action in self._actions.values()
        ]

    def execute(self, name, parameters, *, user_id=None):
        normalized_name = name.strip().lower()

        action = self.get(normalized_name)

        if action is None:
            return ActionResult(
                False, normalized_name,
                "Action is not registered."
            )

        if not isinstance(parameters, dict):
            return ActionResult(
                False, normalized_name,
                "Parameters must be a dictionary."
            )

        if not user_id:
            return ActionResult(
                False, normalized_name,
                "Execution denied: user identity required."
            )

        for permission in action.required_permissions:
            if not self.permissions.has_permission(
                user_id, permission
            ):
                return ActionResult(
                    False, normalized_name,
                    f"Missing permission: {permission}"
                )

        try:
            if not action.validate(parameters):
                return ActionResult(
                    False, normalized_name,
                    "Action parameters are invalid."
                )

            result = action.execute(parameters)

            if not isinstance(result, ActionResult):
                raise TypeError("Action must return ActionResult.")

            return result

        except Exception as error:
            return ActionResult(
                False, normalized_name,
                f"Action execution failed: {type(error).__name__}"
            )
