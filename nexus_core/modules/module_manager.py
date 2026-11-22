from threading import RLock

from nexus_core.modules.base import NexusModule, ModuleStatus


class ModuleManager:
    """Thread-safe lifecycle manager for NEXUS modules."""

    def __init__(self):
        self._modules = {}
        self._lock = RLock()
        self._busy = set()

    @staticmethod
    def _normalize_name(name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid module name.")

        return name.strip().lower()

    def register(self, module):
        if not isinstance(module, NexusModule):
            raise TypeError("Module must inherit NexusModule.")

        name = self._normalize_name(module.name)

        with self._lock:
            if name in self._modules:
                raise ValueError(f"Module already registered: {name}")

            self._modules[name] = module

        return True

    def unregister(self, name):
        name = self._normalize_name(name)

        with self._lock:
            module = self._modules.get(name)

            if module is None:
                return False

            if name in self._busy:
                raise RuntimeError("Module lifecycle operation in progress.")

            if module.status != ModuleStatus.STOPPED:
                raise RuntimeError("Only stopped modules can be removed.")

            del self._modules[name]
            return True

    def get(self, name):
        name = self._normalize_name(name)

        with self._lock:
            return self._modules.get(name)

    def start(self, name):
        name = self._normalize_name(name)

        with self._lock:
            module = self._modules.get(name)

            if module is None:
                return False

            if name in self._busy:
                return False

            if module.status == ModuleStatus.RUNNING:
                return True

            if module.status in (
                ModuleStatus.STARTING,
                ModuleStatus.STOPPING
            ):
                return False

            self._busy.add(name)
            module._status = ModuleStatus.STARTING
            module._last_error = ""

        try:
            module.start()

        except Exception as error:
            with self._lock:
                module._status = ModuleStatus.ERROR
                module._last_error = (
                    f"{type(error).__name__}: {error}"
                )
                self._busy.discard(name)

            return False

        with self._lock:
            module._status = ModuleStatus.RUNNING
            module._last_error = ""
            self._busy.discard(name)

        return True

    def stop(self, name):
        name = self._normalize_name(name)

        with self._lock:
            module = self._modules.get(name)

            if module is None:
                return False

            if name in self._busy:
                return False

            if module.status == ModuleStatus.STOPPED:
                return True

            if module.status != ModuleStatus.RUNNING:
                return False

            self._busy.add(name)
            module._status = ModuleStatus.STOPPING
            module._last_error = ""

        try:
            module.stop()

        except Exception as error:
            with self._lock:
                module._status = ModuleStatus.RUNNING
                module._last_error = (
                    f"{type(error).__name__}: {error}"
                )
                self._busy.discard(name)

            return False

        with self._lock:
            module._status = ModuleStatus.STOPPED
            module._last_error = ""
            self._busy.discard(name)

        return True

    def start_all(self):
        with self._lock:
            names = list(self._modules)

        return {
            name: self.start(name)
            for name in names
        }

    def stop_all(self):
        with self._lock:
            names = list(self._modules)

        return {
            name: self.stop(name)
            for name in reversed(names)
        }

    def list_modules(self):
        with self._lock:
            return [
                {
                    "name": module.name,
                    "version": module.version,
                    "description": module.description,
                    "running": module.is_running,
                    "status": module.status.value,
                    "last_error": module.last_error
                }
                for module in self._modules.values()
            ]

    def count(self):
        with self._lock:
            return len(self._modules)
