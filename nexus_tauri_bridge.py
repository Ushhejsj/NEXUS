import sys
sys.stdout.reconfigure(encoding='utf-8', errors='strict')
sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
sys.stdin.reconfigure(encoding='utf-8', errors='strict')
import json
import time
import secrets
import urllib.request
import urllib.error
import contextlib
import io

BRIDGE_STDOUT = sys.stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Импортируем старые модули, не допуская постороннего вывода в stdout.
with contextlib.redirect_stdout(sys.stderr):
    from core_nexus import build_system_prompt, OLLAMA_URL, OLLAMA_MODEL
    from conversation_memory import ConversationMemory
    from executor import ActionExecutor, _APP_CACHE

CONFIG_PATH = ROOT / "config.json"
CACHE_PATH = ROOT / "app_cache.json"

ALLOWED_ACTIONS = {
    "launch", "volume", "url", "search", "kill", "power",
    "thermal", "macro", "speak", "vision", "food", "window",
    "reminder"
}

DESTRUCTIVE_POWER = {"restart", "shutdown"}
pending = {}
memory = None
executor = None
config = None
system_prompt = None


class BridgeSpeaker:
    def __init__(self):
        self.messages = []

    def say(self, message):
        if message:
            self.messages.append(str(message))


def load_app_cache():
    if not CACHE_PATH.exists():
        return
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        apps = data.get("apps", {})
        if isinstance(apps, dict):
            _APP_CACHE.update(apps)
    except Exception as exc:
        print(f"[NEXUS] Не удалось загрузить кэш приложений: {exc}", file=sys.stderr)


def initialize():
    global memory, executor, config, system_prompt

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    memory = ConversationMemory()
    system_prompt = build_system_prompt(config)

    load_app_cache()

    speaker = BridgeSpeaker()
    executor = ActionExecutor(config, speaker)
    executor.app_cache = _APP_CACHE

    print("[NEXUS] Python bridge initialized.", file=sys.stderr)


def ollama_status():
    try:
        with urllib.request.urlopen("http://localhost:11434", timeout=2):
            return True
    except Exception:
        return False


def interpret(command):
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(memory.get_context_messages())
    messages.append({"role": "user", "content": command})

    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "messages": messages,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "num_predict": 512
        }
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    raw = result.get("message", {}).get("content", "").strip()

    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("Модель вернула ответ без JSON-плана.")

    plan = json.loads(raw[start:end])
    if not isinstance(plan, dict):
        raise ValueError("Некорректный формат плана.")

    return plan


def action_needs_confirmation(action, depth=0):
    if depth > 5 or not isinstance(action, dict):
        return True

    kind = action.get("type")

    if kind not in ALLOWED_ACTIONS:
        raise ValueError(f"Недопустимый тип действия: {kind}")

    if kind == "kill":
        return True

    if kind == "power":
        return str(action.get("command", "")).lower() in DESTRUCTIVE_POWER

    if kind == "macro":
        name = str(action.get("name", "")).strip()
        matched = next(
            (key for key in config.get("macros", {})
             if key.casefold() == name.casefold()),
            None
        )
        if matched is None:
            raise ValueError(f"Макрос «{name}» не найден.")

        macro_actions = config["macros"][matched].get("actions", [])
        return any(
            action_needs_confirmation(item, depth + 1)
            for item in macro_actions
        )

    return False


def validate_plan(plan):
    actions = plan.get("actions", [])
    if not isinstance(actions, list) or len(actions) > 20:
        raise ValueError("Некорректный список действий.")

    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("Некорректное действие.")
        if action.get("type") not in ALLOWED_ACTIONS:
            raise ValueError(f"Неизвестное действие: {action.get('type')}")

        if action.get("type") == "url":
            url = str(action.get("url", ""))
            if not url.startswith(("https://", "http://")):
                raise ValueError("Разрешены только HTTP и HTTPS ссылки.")

    dangerous = any(action_needs_confirmation(a) for a in actions)
    return actions, dangerous


def execute_plan(plan):
    actions = plan.get("actions", [])
    logs = []
    speaker = executor.speaker
    speaker.messages.clear()

    for action in actions:
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                executor.execute(action)
        except Exception as exc:
            logs.append(f"Ошибка: {exc}")
        captured = output.getvalue().strip()
        if captured:
            logs.append(captured)

    logs.extend(speaker.messages)

    return {
        "status": "submitted",
        "speech": str(plan.get("speech", "Команда обработана.")),
        "execution_log": logs
    }


def handle_command(text):
    command = str(text).strip()
    if not command:
        raise ValueError("Введите команду.")

    if len(command) > 2000:
        raise ValueError("Команда слишком длинная.")

    if not ollama_status():
        raise RuntimeError("Ollama не запущена. Сначала запустите локальный Ollama.")

    memory.add("user", command)
    plan = interpret(command)
    actions, dangerous = validate_plan(plan)

    if dangerous or bool(plan.get("requires_confirmation")):
        token = secrets.token_urlsafe(32)
        prompt = str(
            plan.get("confirmation_prompt")
            or "Подтвердить выполнение запрошенного действия?"
        )

        pending[token] = {
            "plan": plan,
            "created": time.time()
        }

        return {
            "status": "confirmation_required",
            "token": token,
            "speech": str(plan.get("speech", "")),
            "confirmation_prompt": prompt
        }

    result = execute_plan(plan)
    memory.add("assistant", result["speech"])
    return result



voice_engine = None
piper_speaker = None

def listen_command():
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 0.6
        recognizer.dynamic_energy_threshold = True

        with sr.Microphone() as source:
            print("[VOICE] Настройка микрофона...", file=sys.stderr)
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            print("[VOICE] Слушаю команду...", file=sys.stderr)
            audio = recognizer.listen(
                source,
                timeout=5,
                phrase_time_limit=10
            )

        transcript = recognizer.recognize_google(
            audio,
            language="ru-RU"
        ).strip()

        if not transcript:
            raise ValueError("Не удалось распознать команду.")

        return {
            "status": "recognized",
            "text": transcript
        }

    except sr.WaitTimeoutError:
        return {"status": "timeout"}
    except sr.UnknownValueError:
        raise RuntimeError("Не удалось разобрать речь. Повторите команду.")
    except sr.RequestError as exc:
        raise RuntimeError(f"Ошибка сервиса распознавания речи: {exc}")
    except OSError as exc:
        raise RuntimeError(f"Проблема с микрофоном: {exc}")


def get_piper_speaker():
    global piper_speaker

    if piper_speaker is None:
        from tts_piper import PiperSpeaker, MODEL_PATH, CONFIG_PATH

        if not Path(MODEL_PATH).is_file() or not Path(CONFIG_PATH).is_file():
            raise RuntimeError(
                "?????? Denis Piper ?? ???????. ?????????????? ???????? ?????????."
            )

        with contextlib.redirect_stdout(sys.stderr):
            speaker = PiperSpeaker()

        if not speaker.is_neural:
            raise RuntimeError("?? ??????? ????????? ???????????? ????? Denis Piper.")

        piper_speaker = speaker

    return piper_speaker



_custom_piper_voice = None
_custom_piper_voice_path = None


def _load_custom_piper_voice(model_path):
    global _custom_piper_voice, _custom_piper_voice_path

    model_path = Path(model_path).resolve()

    if _custom_piper_voice is not None and _custom_piper_voice_path == model_path:
        return _custom_piper_voice

    from tts_piper import PiperVoice, PIPER_AVAILABLE, SD_AVAILABLE

    if not PIPER_AVAILABLE or not SD_AVAILABLE:
        raise RuntimeError("Piper ??? sounddevice ??????????.")

    voice = PiperVoice.load(str(model_path))
    _custom_piper_voice = voice
    _custom_piper_voice_path = model_path
    return voice


def _speak_custom_piper(model_path, text, rate, volume):
    import os
    import tempfile
    import wave
    import sounddevice as sd
    import soundfile as sf
    from tts_piper import SynthesisConfig

    voice = _load_custom_piper_voice(model_path)
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        syn_config = SynthesisConfig(
            length_scale=max(0.70, min(1.80, 1.12 * 185 / rate)),
            noise_scale=0.5,
            noise_w_scale=0.333
        )

        with wave.open(tmp_path, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file, syn_config=syn_config)

        data, sample_rate = sf.read(tmp_path, dtype="float32")
        sd.play(data * volume, samplerate=sample_rate)
        sd.wait()

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _voice_directory(voices_dir):
    if not voices_dir:
        raise RuntimeError("?? ????? ??????? ??????? NEXUS.")
    directory = Path(voices_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def list_voice_options(voices_dir=None):
    voices = [
        {"id": "denis-piper", "name": "Denis \u2014 \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u043d\u0435\u0439\u0440\u043e\u043d\u043d\u044b\u0439 \u0433\u043e\u043b\u043e\u0441"}
    ]

    try:
        import pyttsx3

        global voice_engine
        if voice_engine is None:
            voice_engine = pyttsx3.init()

        system_voices = voice_engine.getProperty("voices") or []
        voices.extend(
            {"id": str(v.id), "name": str(v.name)}
            for v in system_voices
        )
    except Exception as exc:
        print(f"[VOICE] ????????? ?????? ??????????: {exc}", file=sys.stderr)

    if voices_dir:
        directory = _voice_directory(voices_dir)
        for model in sorted(directory.glob("*.onnx")):
            config = Path(str(model) + ".json")
            if not config.is_file():
                continue
            voices.append({
                "id": "piper:" + model.stem,
                "name": model.stem.replace("_", " ") + " \\u2014 Piper"
            })

    return {"voices": voices}


def import_voice_model(source_path, voices_dir):
    import shutil

    source = Path(source_path).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".onnx":
        raise RuntimeError("???????? ???? ?????? Piper ? ??????????? .onnx.")

    source_config = Path(str(source) + ".json")
    if not source_config.is_file():
        raise RuntimeError(
            "????? ? ??????? ?? ?????? ???? ???????????? .onnx.json."
        )

    if source.stat().st_size < 1024 * 1024 or source.stat().st_size > 1024**3:
        raise RuntimeError("?????? ?????? ?????? ???? ?? 1 ?? ?? 1 ??.")

    if source_config.stat().st_size > 5 * 1024 * 1024:
        raise RuntimeError("???? ???????????? ??????? ???????.")

    try:
        config = json.loads(source_config.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"?? ??????? ????????? ???????????? ??????: {exc}")

    if (
        not isinstance(config, dict)
        or not isinstance(config.get("audio"), dict)
        or not isinstance(config.get("phoneme_id_map"), dict)
        or not config["phoneme_id_map"]
    ):
        raise RuntimeError("???????????? ?? ?????? ?? ??????????? ?????? Piper.")

    directory = _voice_directory(voices_dir)

    safe_stem = "".join(
        char if char.isalnum() or char in "-_" else "_"
        for char in source.stem
    ).strip("_")

    if not safe_stem:
        safe_stem = "custom_voice"

    target = directory / f"{safe_stem}.onnx"
    if target.exists() or Path(str(target) + ".json").exists():
        safe_stem += "_" + secrets.token_hex(3)
        target = directory / f"{safe_stem}.onnx"

    target_config = Path(str(target) + ".json")

    try:
        shutil.copy2(source, target)
        shutil.copy2(source_config, target_config)

        # ?????????, ??? Piper ????????????? ????? ????????? ??????.
        _load_custom_piper_voice(target)

        global _custom_piper_voice, _custom_piper_voice_path
        _custom_piper_voice = None
        _custom_piper_voice_path = None

    except Exception as exc:
        target.unlink(missing_ok=True)
        target_config.unlink(missing_ok=True)
        raise RuntimeError(f"?? ??????? ?????????? ????? Piper: {exc}")

    return {
        "id": "piper:" + safe_stem,
        "name": safe_stem.replace("_", " ") + " \u2014 Piper"
    }


def speak_text(text, settings=None, voices_dir=None):
    global voice_engine

    text = str(text).strip()
    if not text:
        return {"status": "ok"}

    settings = settings if isinstance(settings, dict) else {}
    selected_id = settings.get("voiceId")

    try:
        rate = max(100, min(300, int(settings.get("rate", 185))))
        volume = max(0.0, min(1.0, float(settings.get("volume", 1.0))))

        if not selected_id or selected_id == "denis-piper":
            speaker = get_piper_speaker()
            speaker.say(text, rate=rate, volume=volume)
            return {"status": "ok", "voice": "denis-piper"}

        if str(selected_id).startswith("piper:"):
            directory = _voice_directory(voices_dir)
            stem = str(selected_id)[6:]

            if not stem or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in stem):
                raise RuntimeError("???????????? ????????????? ??????.")

            model_path = (directory / f"{stem}.onnx").resolve()
            if model_path.parent != directory or not model_path.is_file():
                raise RuntimeError("????????????? ?????? ?????? ?? ???????.")

            if not Path(str(model_path) + ".json").is_file():
                raise RuntimeError("???????????? ?????? ?? ???????.")

            _speak_custom_piper(model_path, text, rate, volume)
            return {"status": "ok", "voice": selected_id}

        import pyttsx3

        if voice_engine is None:
            voice_engine = pyttsx3.init()

        voices = voice_engine.getProperty("voices") or []
        matching = next(
            (voice for voice in voices if str(voice.id) == str(selected_id)),
            None
        )

        if matching is None:
            raise RuntimeError("????????? ????????? ????? ?? ??????.")

        voice_engine.setProperty("voice", matching.id)
        voice_engine.setProperty("rate", rate)
        voice_engine.setProperty("volume", volume)
        voice_engine.say(text)
        voice_engine.runAndWait()

        return {"status": "ok", "voice": str(selected_id)}

    except Exception as exc:
        raise RuntimeError(f"?????? ???????????: {exc}")


def handle_request(request):
    op = request.get("op")

    if op == "status":
        return {
            "status": "online",
            "ollama": ollama_status(),
            "model": OLLAMA_MODEL,
            "cached_apps": len(_APP_CACHE)
        }

    if op == "listen":
        return listen_command()

    if op == "list_voices":
        return list_voice_options(request.get("voices_dir"))

    if op == "import_voice":
        return import_voice_model(
            request.get("source_path", ""),
            request.get("voices_dir")
        )

    if op == "speak":
        return speak_text(
            request.get("text", ""),
            request.get("settings"),
            request.get("voices_dir")
        )

    if op == "command":
        return handle_command(request.get("text", ""))

    if op in ("confirm", "cancel"):
        token = str(request.get("token", ""))
        item = pending.pop(token, None)

        if not item:
            raise ValueError("Подтверждение не найдено или уже истекло.")

        if time.time() - item["created"] > 180:
            raise ValueError("Время подтверждения истекло.")

        if op == "cancel":
            memory.add("assistant", "Выполнение отменено.")
            return {"status": "cancelled", "speech": "Выполнение отменено."}

        # Повторная проверка непосредственно перед исполнением.
        validate_plan(item["plan"])
        result = execute_plan(item["plan"])
        memory.add("assistant", result["speech"])
        return result

    raise ValueError("Неизвестная операция моста.")


def main():
    # Служебный вывод всех модулей направляем в stderr.
    with contextlib.redirect_stdout(sys.stderr):
        initialize()

    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("Некорректный запрос.")

            with contextlib.redirect_stdout(sys.stderr):
                response = handle_request(request)

        except urllib.error.URLError as exc:
            response = {"status": "error", "error": f"Ошибка Ollama: {exc}"}
        except Exception as exc:
            response = {"status": "error", "error": str(exc)}

        # В stdout отправляется только JSON-ответ для Rust.
        BRIDGE_STDOUT.write(json.dumps(response, ensure_ascii=False) + "\n")
        BRIDGE_STDOUT.flush()

if __name__ == "__main__":
    main()

