class PermissionManager:
    """Central permission management for NEXUS actions."""

    def __init__(self):
        self._permissions = {}

    def grant(self, user_id: str, permission: str):
        self._validate(user_id, permission)

        self._permissions.setdefault(user_id, set())
        self._permissions[user_id].add(permission)

        return True

    def revoke(self, user_id: str, permission: str):
        self._validate(user_id, permission)

        permissions = self._permissions.get(user_id)

        if not permissions:
            return False

        permissions.discard(permission)

        if not permissions:
            self._permissions.pop(user_id, None)

        return True

    def has_permission(self, user_id: str, permission: str):
        if not user_id or not permission:
            return False

        permissions = self._permissions.get(user_id, set())

        return (
            permission in permissions
            or "admin" in permissions
        )

    def get_permissions(self, user_id: str):
        return sorted(self._permissions.get(user_id, set()))

    def clear(self, user_id: str):
        return self._permissions.pop(user_id, None) is not None

    @staticmethod
    def _validate(user_id, permission):
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Invalid user ID.")

        if not isinstance(permission, str) or not permission.strip():
            raise ValueError("Invalid permission.")
