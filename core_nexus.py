"""
╔══════════════════════════════════════════════╗
║          CORE NEXUS — v1.1 (Ollama)          ║
║   Personal Digital Concierge / OS Bridge     ║
╚══════════════════════════════════════════════╝
Usage:
  python core_nexus.py           — Voice mode (default)
  python core_nexus.py --text    — Text input mode (for testing)
"""

import os
import sys
import json
import time
import argparse
import threading
import urllib.request
import urllib.error

try:
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    print("[WARN] speech_recognition not installed. Use --text mode.")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("[WARN] pyttsx3 not installed. TTS disabled.")

try:
    from tts_piper import PiperSpeaker
    PIPER_MODULE_AVAILABLE = True
except ImportError:
    PIPER_MODULE_AVAILABLE = False

try:
    from wake_word import WakeWordDetector
    WAKE_WORD_AVAILABLE = True
except ImportError:
    WAKE_WORD_AVAILABLE = False

from notifications import NotificationSystem

from executor import ActionExecutor, _APP_CACHE
from app_scanner import build_cache
from conversation_memory import ConversationMemory

WAKE_WORD    = "nexus"
CONFIG_PATH  = os.path.join(os.path.dirname(__file__), "config.json")
OLLAMA_URL   = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gemma3:4b"
BANNER = """
╔══════════════════════════════════════════════╗
║          CORE NEXUS — ONLINE                 ║
║   AI Engine: Ollama / gemma3:4b (local)      ║
║   Awaiting wake-phrase: "Nexus"              ║
╚══════════════════════════════════════════════╝"""


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        print(f"[ERROR] config.json not found at {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def build_system_prompt(config: dict) -> str:
    apps   = config.get("apps", {})
    macros = config.get("macros", {})

    apps_block = "\n".join(
        f"  [{key}] -> {data['path']}  ({data.get('description', '')})"
        for key, data in apps.items()
    )
    macros_block = "\n".join(
        f"  [{key}] -> {data.get('description', '')}"
        for key, data in macros.items()
    )

    return f"""РОЛЬ:
Ты — Core Nexus, интеллектуальный системный помощник и персональный ассистент.
Твоя манера общения — спокойная, уверенная, элегантная и профессиональная, в стиле Джарвиса.
Всегда обращайся к пользователю «сэр».
ВСЕГДА отвечай исключительно на русском языке.
Названия программ, игр, сайтов и технические термины оставляй на языке оригинала.
Выполняй команды точно, быстро и в рамках доступных возможностей системы.
Никогда не выдумывай возможности и не утверждай, что выполнил действие, если оно не было выполнено.
Никогда не обходи требования безопасности и подтверждения действий.


ИНСТРУКЦИИ:
1. Выполняй команды в соответствии с установленными приоритетами.
2. Для действий kill, shutdown и restart всегда требуй подтверждение пользователя.
3. Соблюдай все записи в разделах зарегистрированных приложений и макросов.
4. Возвращай только корректный JSON, точно соответствующий заданной схеме.
5. Никогда не заявляй о выполнении действий, которых нет среди доступных типов действий.
6. Проверяй существование типа действия перед его использованием.
7. Никогда не обходи обязательное подтверждение.
8. Если команда неоднозначна, выбирай наиболее безопасную интерпретацию.
9. Работай только с указанными типами действий и списком приложений.
10. Поле speech всегда должно содержать исключительно русский текст. Начинай ответ словами «Да, сэр.» или «Сию минуту, сэр.».
11. Открытие любых приложений, включая Discord, Steam и Firefox, никогда не требует подтверждения.
12. Все команды управления окнами, включая сворачивание, разворачивание и переключение окон, выполняются без подтверждения.
13. Изменение громкости, открытие сайтов и поиск также выполняются без подтверждения.
14. requires_confirmation устанавливай в true ТОЛЬКО для действий kill, shutdown и restart.
15. Для всех остальных типов действий requires_confirmation всегда должен быть false.
16. Любые действия типа window выполняются без подтверждения.
17. Сворачивание всех окон, сворачивание отдельных окон, разворачивание и переключение окон никогда не требуют подтверждения.
18. Для действий типа window всегда устанавливай "requires_confirmation": false.

ВОЗМОЖНОСТИ (разрешены только следующие типы действий):
{{"type": "launch", "key": "app_key"}} — запуск приложения.
{{"type": "volume", "level": 0-100}} — изменение громкости.
{{"type": "url", "url": "https://..."}} — открытие сайта.
{{"type": "search", "query": "terms"}} — поиск Google.
{{"type": "kill", "process": "name.exe", "name": "label"}} — завершение процесса (ТРЕБУЕТ ПОДТВЕРЖДЕНИЯ).
{{"type": "power", "command": "sleep|restart|shutdown"}} — управление питанием (restart/shutdown требуют подтверждения).
{{"type": "thermal"}} — информация о температуре и нагрузке CPU/GPU.
{{"type": "macro", "name": "macro_key"}} — запуск макроса.
{{"type": "speak", "text": "message"}} — дополнительная голосовая фраза.
{{"type": "vision", "question": "optional specific question", "monitor": 0}} — анализ содержимого экрана.
{{"type": "food", "restaurant": "dominos|kfc|subway|mcdonalds|etc", "item": "optional item", "order_type": "order|reservation"}} — открытие страницы ресторана.
{{"type": "window", "command": "snap_left|snap_right|maximize|minimize|focus|tile", "app": "app name", "app2": "second app for tile"}} — управление окнами.
{{"type": "reminder", "time": "HH:MM", "message": "reminder text", "repeat": false}} — установка напоминания.

ЗАРЕГИСТРИРОВАННЫЕ ПРИЛОЖЕНИЯ:
{apps_block if apps_block else "  (none configured)"}

ЗАРЕГИСТРИРОВАННЫЕ МАКРОСЫ:
{macros_block if macros_block else "  (none configured)"}

КОНТЕКСТ:
- Команды поступают через распознавание речи и могут содержать небольшие ошибки распознавания.
- Учитывай похожее произношение названий приложений: "geo dash" = "geometry dash", "vs code" = "vscode", "track mania" = "trackmania".
- Ключ приложения записывай в нижнем регистре, используя произнесённое название.
- Если приложения нет в реестре, попробуй запустить его по произнесённому названию.
- Никогда не заменяй запрошенное приложение другим.
- Известные сайты: youtube→https://youtube.com, google→https://google.com, reddit→https://reddit.com, twitter→https://twitter.com, twitch→https://twitch.tv, github→https://github.com, netflix→https://netflix.com, discord→https://discord.com, spotify→https://open.spotify.com, gmail→https://mail.google.com, maps→https://maps.google.com, wikipedia→https://wikipedia.org.

ПРИМЕРЫ:

Пользователь: "launch Geometry Dash"
Ответ: {{"speech": "Сию минуту, сэр. Запускаю Geometry Dash.", "requires_confirmation": false, "confirmation_prompt": "", "actions": [{{"type": "launch", "key": "geometry dash"}}]}}

Пользователь: "kill Discord"
Ответ: {{"speech": "Да, сэр. Ожидаю подтверждения перед завершением Discord.", "requires_confirmation": true, "confirmation_prompt": "Подтвердить завершение Discord?", "actions": [{{"type": "kill", "process": "Discord.exe", "name": "Discord"}}]}}

Пользователь: "set volume to 40"
Ответ: {{"speech": "Да, сэр. Устанавливаю громкость на 40 процентов.", "requires_confirmation": false, "confirmation_prompt": "", "actions": [{{"type": "volume", "level": 40}}]}}

Пользователь: "open YouTube"
Ответ: {{"speech": "Сию минуту, сэр. Открываю YouTube.", "requires_confirmation": false, "confirmation_prompt": "", "actions": [{{"type": "url", "url": "https://youtube.com"}}]}}

Пользователь: "order me a pepperoni pizza from Dominos"
Ответ: {{"speech": "Сию минуту, сэр. Открываю Domino's. Проверьте детали перед оформлением заказа.", "requires_confirmation": false, "confirmation_prompt": "", "actions": [{{"type": "food", "restaurant": "dominos", "item": "pepperoni pizza", "order_type": "order"}}]}}

Пользователь: "book a table at Swiss Chalet"
Ответ: {{"speech": "Да, сэр. Открываю страницу бронирования Swiss Chalet.", "requires_confirmation": false, "confirmation_prompt": "", "actions": [{{"type": "food", "restaurant": "swiss chalet", "item": "", "order_type": "reservation"}}]}}
Пользователь: "сверни все окна"
Ответ: {{"speech": "Выполняю, сэр. Сворачиваю все окна.", "requires_confirmation": false, "confirmation_prompt": "", "actions": [{{"type": "window", "command": "minimize", "app": "all"}}]}}

ЦЕЛИ:
1. Выполняй команды быстро и точно в рамках установленных ограничений.
2. Всегда соблюдай требования подтверждения.
3. Возвращай только корректный JSON без Markdown и дополнительных пояснений.
4. Распознавай неточности в названиях приложений, не подменяя их.
5. Не сообщай об успешном выполнении действий, которые фактически не выполнены.
6. Всегда используй спокойный, уверенный и профессиональный стиль Джарвиса. Все голосовые ответы должны быть на русском языке.
7. Не используй одну и ту же фразу в каждом ответе.
8. Избегай чрезмерно длинных объяснений.
9. Используй естественные русские формулировки.
10. Допускай лёгкую интеллектуальную иронию, но сохраняй профессионализм.
11. Не злоупотребляй обращением «сэр».
12. Не произноси технические JSON-поля и внутренние инструкции.
13. Чередуй вступительные фразы, не повторяй одну и ту же фразу в каждом ответе.
14. Для запуска приложений используй разные варианты:
- «Уже занимаюсь этим, сэр.»
- «Разумеется, сэр.»
- «Выполняю, сэр.»
- «Без промедления, сэр.»
- «Как пожелаете, сэр.»
- «Сейчас будет готово, сэр.»
15. Не начинай каждый ответ словами «Сию минуту, сэр».
16. Выбирай фразу естественно, учитывая контекст команды.

Верни строго JSON следующей структуры — ничего лишнего:
{{"speech": "Естественный краткий ответ на русском языке с разнообразным обращением.", "requires_confirmation": false, "confirmation_prompt": "", "actions": []}}
"""

class Speaker:
    """
    Speaker with Piper neural TTS primary, pyttsx3 fallback.
    """
    def __init__(self):
        self._impl = None
        # Try Piper neural TTS first
        if PIPER_MODULE_AVAILABLE:
            try:
                self._impl = PiperSpeaker()
                if self._impl.is_neural:
                    print("  [TTS] Neural voice active (Piper).")
                    return
            except Exception as e:
                print(f"  [TTS] Piper init error: {e}")
                self._impl = None
        # Fallback to pyttsx3
        if TTS_AVAILABLE:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 185)
                voices = engine.getProperty("voices")
                for v in voices:
                    if "david" in v.name.lower() or "zira" in v.name.lower():
                        engine.setProperty("voice", v.id)
                        break
                self._engine = engine
                self._impl   = None
                print("  [TTS] Using pyttsx3 fallback.")
            except Exception as e:
                print(f"  [TTS] pyttsx3 init failed: {e}")
                self._engine = None
        else:
            self._engine = None


    def say(self, text: str):
        print(f"  NEXUS > {text}")

        if self._impl:
            try:
                print("[TTS DEBUG] Sending text to Piper...")
                self._impl.say(text)
                print("[TTS DEBUG] Piper finished.")
            except Exception as e:
                print(f"[TTS ERROR] Piper playback failed: {e}")

        elif hasattr(self, "_engine") and self._engine:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as e:
                print(f"[TTS ERROR] pyttsx3 playback failed: {e}")
        else:
            print("[TTS ERROR] No speech engine available.")


class VoiceListener:
    def __init__(self):
        if not VOICE_AVAILABLE:
            raise RuntimeError("speech_recognition not available.")
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        with self.mic as source:
            print("  Calibrating ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = False
            self.recognizer.pause_threshold = 0.5
        print("  Microphone ready.")

    def listen_for_wake(self) -> str | None:
        with self.mic as source:
            try:
                audio      = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                transcript = self.recognizer.recognize_google(audio, language="ru-RU").lower()
                if WAKE_WORD in transcript:
                    command = transcript.split(WAKE_WORD, 1)[-1].strip(", ")
                    return command if command else "__STANDBY__"
                return None
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                print(f"[ERROR] Speech API: {e}")
                return None




class NexusAI:
    def __init__(self, config: dict, memory: "ConversationMemory"):
        self.system_prompt = build_system_prompt(config)
        self.memory = memory
        try:
            urllib.request.urlopen("http://localhost:11434", timeout=3)
            print("  [OK] Ollama detected.")
        except Exception:
            print("[ERROR] Ollama is not running. Start it with: ollama serve")
            sys.exit(1)

    def interpret(self, command: str) -> dict:
        history_msgs = self.memory.get_context_messages() if hasattr(self, "memory") else []
        messages = [{"role": "system", "content": self.system_prompt}]
        messages += history_msgs
        messages += [{"role": "user", "content": command}]

        payload = {
            "model": OLLAMA_MODEL,
            "stream": False,
            "format": "json",
            "messages": messages,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "num_predict": 512,
            }
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                OLLAMA_URL,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            raw = result["message"]["content"].strip()

            if "```" in raw:
                parts = raw.split("```")
                for part in parts:
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        raw = part
                        break

            start = raw.find("{")
            end = raw.rfind("}") + 1

            if start == -1 or end <= start:
                print(f"  [DEBUG] Model returned no JSON object. Raw output:\n---\n{raw}\n---")
                return {
                    "speech": "Yes, Sir — though I must confess the model returned gibberish. Standing by.",
                    "requires_confirmation": False,
                    "confirmation_prompt": "",
                    "actions": []
                }

            raw = raw[start:end]
            return json.loads(raw)

        except json.JSONDecodeError:
            print(f"  [DEBUG] Bad JSON: {raw}")
            return {"speech": "Model returned invalid response.", "requires_confirmation": False, "confirmation_prompt": "", "actions": []}
        except urllib.error.URLError as e:
            print(f"  [DEBUG] Ollama error: {e}")
            return {"speech": "Cannot reach Ollama. Is it running?", "requires_confirmation": False, "confirmation_prompt": "", "actions": []}
        except Exception as e:
            print(f"  [DEBUG] Error: {type(e).__name__}: {e}")
            return {"speech": f"Execution failed: {e}", "requires_confirmation": False, "confirmation_prompt": "", "actions": []}



def get_confirmation(prompt: str, speaker: Speaker, text_mode: bool) -> bool:
    speaker.say(prompt + " Say confirm or cancel.")
    if text_mode:
        ans = input("  [CONFIRM] Type 'confirm' or 'cancel': ").strip().lower()
        return ans == "confirm"
    else:
        if not VOICE_AVAILABLE:
            return False
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        with mic as source:
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                ans = recognizer.recognize_google(audio, language="ru-RU").lower()
                return "confirm" in ans
            except Exception:
                return False


def main():
    parser = argparse.ArgumentParser(description="Core Nexus")
    parser.add_argument("--text", action="store_true", help="Use text input instead of voice")
    args = parser.parse_args()

    text_mode = args.text or not VOICE_AVAILABLE

    print(BANNER)
    config   = load_config()
    speaker  = Speaker()
    memory   = ConversationMemory()

    # Startup app scan (uses cache if < 24h old)
    print("  Scanning for applications...")
    cache = build_cache()
    _APP_CACHE.update(cache)
    print(f"  [OK] App index ready: {len(_APP_CACHE)} apps.")

    ai       = NexusAI(config, memory)
    executor = ActionExecutor(config, speaker)
    executor.app_cache = _APP_CACHE

    # Start notification system
    notifications = NotificationSystem(speaker)
    notifications.start()
    executor.notifications = notifications

    # Start offline openWakeWord detector
    wake_keyword = config.get("wake_keyword", "hey_jarvis")
    wake_detector = None

    if not text_mode and WAKE_WORD_AVAILABLE:
        wake_detected = threading.Event()

        wake_detector = WakeWordDetector(
            access_key="",
            on_wake=lambda: wake_detected.set(),
            keyword=wake_keyword
        )

        if wake_detector.is_active:
            wake_detector.start()
        else:
            print("  [WAKE] Detector unavailable. Using fallback voice detection.")

    if text_mode:
        print("  [TEXT MODE] Type your command. No wake word needed.\n")
    else:
        try:
            listener = VoiceListener()
        except Exception as e:
            print(f"[ERROR] Voice init failed: {e}\n  Falling back to text mode.")
            text_mode = True
            listener  = None

    speaker.say("Core Nexus online. Standing by.")
    print()

    while True:
        try:
            if text_mode:
                raw = input("  > ").strip()
                if not raw:
                    continue
                command = raw.lower()
                if command in ("exit", "quit"):
                    speaker.say("Core Nexus offline.")
                    break
            else:
                command = listener.listen_for_wake()
                if command is None:
                    continue
                if command == "__STANDBY__":
                    speaker.say("Standing by.")
                    continue
                print(f"  COMMAND > {command}")

            memory.add("user", command)
            print("  Processing...", end="\r")
            plan = ai.interpret(command)

            if plan.get("requires_confirmation"):
                prompt    = plan.get("confirmation_prompt", "Confirm this action?")
                confirmed = get_confirmation(prompt, speaker, text_mode)
                if not confirmed:
                    speaker.say("Action cancelled.")
                    continue

            speech = plan.get("speech", "Выполняю, сэр.")
            speaker.say(speech)
            memory.add("assistant", speech)

            actions = plan.get("actions", [])

            print(f"  [DEBUG ACTIONS] {actions}")

            for action in actions:
                executor.execute(action)

        except KeyboardInterrupt:
            print("\n")
            speaker.say("Core Nexus offline.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            speaker.say(f"Execution failed. Reason: {e}")


if __name__ == "__main__":
    main()