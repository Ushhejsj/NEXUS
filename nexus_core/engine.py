from pathlib import Path

from nexus_core.config import NexusConfig
from nexus_core.config_manager import ConfigManager
from nexus_core.providers.base import BaseAIProvider
from nexus_core.providers.ollama_provider import OllamaProvider
from nexus_core.memory.conversation_memory import ConversationMemory
from nexus_core.actions.action_registry import ActionRegistry
from nexus_core.actions.permission_manager import PermissionManager
from nexus_core.actions.base import BaseAction
from nexus_core.events.event import NexusEvent
from nexus_core.events.event_bus import EventBus
from nexus_core.state.runtime_state import RuntimeState
from nexus_core.modules.base import NexusModule
from nexus_core.modules.module_manager import ModuleManager


DEFAULT_SYSTEM_PROMPT = """
Ты — AI-ассистент CORE NEXUS.
Отвечай на языке пользователя.
Отвечай прямо на вопрос.
Не выдумывай факты.
Если не знаешь ответа — скажи об этом.
Предпочитай краткие и точные ответы.
"""


class NexusEngine:
    """Central AI engine for CORE NEXUS."""

    def __init__(
        self,
        config: NexusConfig | None = None,
        provider: BaseAIProvider | None = None,
        memory: ConversationMemory | None = None,
        event_bus: EventBus | None = None,
        config_manager: ConfigManager | None = None
    ):
        if config is not None and config_manager is not None:
            raise ValueError(
                "Provide config or config_manager, not both."
            )

        self.config_manager = config_manager or (
            ConfigManager() if config is None else None
        )

        if self.config_manager is not None:
            self.config = self.config_manager.load()
        else:
            self.config = config

        self.provider = provider or self._create_provider()

        if not isinstance(self.provider, BaseAIProvider):
            raise TypeError("Provider must implement BaseAIProvider.")

        memory_path = (
            Path(__file__).parent
            / "memory"
            / "nexus_engine_memory.json"
        )

        self.memory = memory or ConversationMemory(
            storage_path=memory_path,
            max_messages=self.config.context_messages * 2
        )

        self.permissions = PermissionManager()
        self.actions = ActionRegistry(self.permissions)
        self.events = event_bus or EventBus()
        self.modules = ModuleManager()

        self.state = RuntimeState(
            provider=self.config.provider,
            model=self.config.model
        )

        self.publish_event("nexus.started", {
            "provider": self.config.provider,
            "model": self.config.model
        })

    @property
    def history(self):
        return [
            {"role": item["role"], "content": item["content"]}
            for item in self.memory.get_history()
        ]

    def publish_event(self, name, data=None):
        result = self.events.publish(
            NexusEvent(name=name, data=data or {})
        )

        self.state.record_event()
        return result

    def subscribe(self, event_name, callback):
        return self.events.subscribe(event_name, callback)

    def unsubscribe(self, event_name, callback):
        return self.events.unsubscribe(event_name, callback)

    def get_state(self):
        return self.state.get_snapshot()

    def register_module(self, module: NexusModule):
        result = self.modules.register(module)

        self.publish_event("module.registered", {
            "module": module.name
        })

        return result

    def unregister_module(self, name):
        result = self.modules.unregister(name)

        if result:
            self.publish_event("module.unregistered", {
                "module": name
            })

        return result

    def start_module(self, name):
        result = self.modules.start(name)

        self.publish_event(
            "module.started" if result else "module.error",
            {"module": name, "operation": "start", "success": result}
        )

        return result

    def stop_module(self, name):
        result = self.modules.stop(name)

        self.publish_event(
            "module.stopped" if result else "module.error",
            {"module": name, "operation": "stop", "success": result}
        )

        return result

    def start_all_modules(self):
        results = self.modules.start_all()

        for name, success in results.items():
            self.publish_event(
                "module.started" if success else "module.error",
                {"module": name, "operation": "start", "success": success}
            )

        return results

    def stop_all_modules(self):
        results = self.modules.stop_all()

        for name, success in results.items():
            self.publish_event(
                "module.stopped" if success else "module.error",
                {"module": name, "operation": "stop", "success": success}
            )

        return results

    def list_modules(self):
        return self.modules.list_modules()


    def _create_provider(self):
        if self.config.provider.lower() == "ollama":
            return OllamaProvider(self.config)

        raise ValueError(
            f"Unsupported AI provider: {self.config.provider}"
        )

    def check_connection(self):
        try:
            result = self.provider.check_connection()

            if result.get("connected"):
                self.state.clear_error()
                self.state.set_status("running")
            else:
                self.state.set_error("AI provider is unavailable.")

            return result

        except Exception as error:
            self.state.set_error(type(error).__name__)
            raise

    def reset_history(self):
        self.memory.clear()
        self.state.update_activity()

    def register_action(self, action: BaseAction):
        result = self.actions.register(action)

        self.publish_event("action.registered", {
            "action": action.name
        })

        return result

    def list_actions(self):
        return self.actions.list_actions()

    def grant_permission(self, user_id, permission):
        result = self.permissions.grant(user_id, permission)

        self.publish_event("permission.granted", {
            "user_id": user_id,
            "permission": permission
        })

        return result

    def revoke_permission(self, user_id, permission):
        result = self.permissions.revoke(user_id, permission)

        if result:
            self.publish_event("permission.revoked", {
                "user_id": user_id,
                "permission": permission
            })

        return result

    def execute_action(self, name, parameters, user_id):
        result = self.actions.execute(
            name,
            parameters,
            user_id=user_id
        )

        event_name = (
            "action.executed"
            if result.success
            else "permission.denied"
            if result.message.startswith("Missing permission")
            or result.message.startswith("Execution denied")
            else "action.failed"
        )

        self.publish_event(event_name, {
            "action": name,
            "user_id": user_id,
            "success": result.success,
            "message": result.message
        })

        return result.to_dict()

    def chat(self, message: str, system_prompt: str | None = None):
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        self.state.update_activity()

        try:
            messages = [{
                "role": "system",
                "content": system_prompt or DEFAULT_SYSTEM_PROMPT
            }]

            messages.extend(self.history)
            messages.append({
                "role": "user",
                "content": message.strip()
            })

            response = self.provider.chat(messages)

            if not isinstance(response, str) or not response.strip():
                raise RuntimeError(
                    "AI provider returned an empty response."
                )

            response = response.strip()

            self.memory.add("user", message)
            self.memory.add("assistant", response)

            result = {
                "success": True,
                "response": response,
                "history_messages": self.memory.count(),
                "provider": self.config.provider,
                "model": self.config.model
            }

            self.publish_event("ai.response", {
                "provider": self.config.provider,
                "model": self.config.model,
                "history_messages": self.memory.count()
            })

            return result

        except Exception as error:
            self.state.set_error(type(error).__name__)
            self.publish_event("ai.error", {
                "error": type(error).__name__
            })
            raise
