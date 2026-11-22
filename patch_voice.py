from pathlib import Path
import shutil

bridge_path = Path("nexus_tauri_bridge.py")
rust_path = Path("nexus_ui/tauri/src-tauri/src/lib.rs")

bridge = bridge_path.read_text(encoding="utf-8")

marker = "\ndef handle_request(request):"
insert = r'''

voice_engine = None

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
        raise RuntimeError("Не услышал речь. Попробуйте ещё раз.")
    except sr.UnknownValueError:
        raise RuntimeError("Не удалось разобрать речь. Повторите команду.")
    except sr.RequestError as exc:
        raise RuntimeError(f"Ошибка сервиса распознавания речи: {exc}")
    except OSError as exc:
        raise RuntimeError(f"Проблема с микрофоном: {exc}")


def speak_text(text):
    global voice_engine

    text = str(text).strip()
    if not text:
        return {"status": "ok"}

    try:
        import pyttsx3

        if voice_engine is None:
            voice_engine = pyttsx3.init()
            voice_engine.setProperty("rate", 185)

            voices = voice_engine.getProperty("voices")
            for voice in voices:
                name = str(voice.name).lower()
                if "russian" in name or "рус" in name:
                    voice_engine.setProperty("voice", voice.id)
                    break

        voice_engine.say(text)
        voice_engine.runAndWait()
        return {"status": "ok"}

    except Exception as exc:
        raise RuntimeError(f"Ошибка голосового движка: {exc}")
'''

if marker not in bridge:
    raise SystemExit("Не найдена точка вставки в Python bridge.")
if "def listen_command():" in bridge:
    raise SystemExit("Голосовые функции уже присутствуют. Файл не изменён.")

bridge = bridge.replace(marker, insert + marker, 1)

marker = '    if op == "command":\n        return handle_command(request.get("text", ""))'
replacement = '''    if op == "listen":
        return listen_command()

    if op == "speak":
        return speak_text(request.get("text", ""))

    if op == "command":
        return handle_command(request.get("text", ""))'''

if marker not in bridge:
    raise SystemExit("Не найдена точка вставки операций Python bridge.")

bridge = bridge.replace(marker, replacement, 1)

rust = rust_path.read_text(encoding="utf-8")

marker = "\npub fn run() {"
insert = r'''

#[tauri::command]
async fn nexus_core_listen(
    state: tauri::State<'_, Arc<Mutex<CoreBridge>>>,
) -> Result<Value, String> {
    let bridge = state.inner().clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut bridge = bridge
            .lock()
            .map_err(|_| "Блокировка Python-ядра повреждена.".to_string())?;
        bridge.call(json!({"op": "listen"}))
    })
    .await
    .map_err(|e| format!("Ошибка голосового ввода: {e}"))?
}

#[tauri::command]
async fn nexus_core_speak(
    state: tauri::State<'_, Arc<Mutex<CoreBridge>>>,
    text: String,
) -> Result<Value, String> {
    let bridge = state.inner().clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut bridge = bridge
            .lock()
            .map_err(|_| "Блокировка Python-ядра повреждена.".to_string())?;
        bridge.call(json!({"op": "speak", "text": text}))
    })
    .await
    .map_err(|e| format!("Ошибка голосового ответа: {e}"))?
}
'''

if marker not in rust:
    raise SystemExit("Не найдена точка вставки в Rust.")
if "async fn nexus_core_listen(" in rust:
    raise SystemExit("Голосовые команды уже присутствуют в Rust.")

rust = rust.replace(marker, insert + marker, 1)

handler_marker = "            nexus_core_status,"
if handler_marker not in rust:
    raise SystemExit("Не найдена регистрация nexus_core_status.")

rust = rust.replace(
    handler_marker,
    handler_marker + "\n            nexus_core_listen,\n            nexus_core_speak,",
    1
)

shutil.copy2(bridge_path, bridge_path.with_suffix(".py.voice-backup"))
shutil.copy2(rust_path, rust_path.with_suffix(".rs.voice-backup"))

bridge_path.write_text(bridge, encoding="utf-8")
rust_path.write_text(rust, encoding="utf-8")

print("VOICE BACKEND PATCH OK")
