from pathlib import Path

tsx = Path("nexus_ui/tauri/src/components/NexusConsole.tsx")
css = Path("nexus_ui/tauri/src/components/NexusConsole.css")

s = tsx.read_text(encoding="utf-8")

def replace_once(old, new, label):
    global s
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: ожидалось одно совпадение, найдено {count}")
    s = s.replace(old, new, 1)

replace_once(
    'import { Send, Cpu, ShieldCheck, X, LoaderCircle, AlertCircle } from "lucide-react";',
    'import { Send, Mic, Cpu, ShieldCheck, X, LoaderCircle, AlertCircle } from "lucide-react";',
    "Импорт Mic"
)

replace_once(
    '  error?: string;\n};',
    '  error?: string;\n  text?: string;\n};',
    "Поле распознанного текста"
)

replace_once(
    '  const [busy, setBusy] = useState(false);',
    '  const [busy, setBusy] = useState(false);\n  const [listening, setListening] = useState(false);',
    "Состояние микрофона"
)

replace_once(
    '  function showResponse(response: CoreResponse) {\n    if (response.speech) addMessage("assistant", response.speech);',
    '''  function speakResponse(text: string) {
    void invoke<CoreResponse>("nexus_core_speak", { text }).catch((error) => {
      addMessage("system", `Ошибка озвучивания: ${String(error)}`);
    });
  }

  function showResponse(response: CoreResponse) {
    if (response.speech) {
      addMessage("assistant", response.speech);
      speakResponse(response.speech);
    }''',
    "Озвучивание ответов"
)

replace_once(
    '        if (response.speech) addMessage("assistant", response.speech);',
    '''        if (response.speech) {
          addMessage("assistant", response.speech);
          speakResponse(response.speech);
        }''',
    "Озвучивание подтверждения"
)

marker = '  async function resolveConfirmation(confirmed: boolean) {'
listen_function = '''  async function listenCommand() {
    if (busy || pending) return;

    setBusy(true);
    setListening(true);

    try {
      const result = await invoke<CoreResponse>("nexus_core_listen");
      const value = result.text?.trim();

      if (!value) {
        throw new Error("Речь не распознана. Попробуйте ещё раз.");
      }

      addMessage("user", value);

      const response = await invoke<CoreResponse>("nexus_core_command", {
        text: value
      });

      if (response.status === "confirmation_required" && response.token) {
        setPending({
          token: response.token,
          prompt: response.confirmation_prompt || "Подтвердить выполнение действия?"
        });

        if (response.speech) {
          addMessage("assistant", response.speech);
          speakResponse(response.speech);
        }
      } else {
        showResponse(response);
      }
    } catch (error) {
      addMessage("system", `Ошибка голосового ввода: ${String(error)}`);
    } finally {
      setListening(false);
      setBusy(false);
    }
  }

'''
replace_once(marker, listen_function + marker, "Обработчик микрофона")

replace_once(
    '        addMessage("assistant", response.speech || "Выполнение отменено.");',
    '''        const message = response.speech || "Выполнение отменено.";
        addMessage("assistant", message);
        speakResponse(message);''',
    "Озвучивание отмены"
)

replace_once(
    '      <div className="nexus-console-input-row">\n        <textarea',
    '''      <div className="nexus-console-input-row">
        <textarea''',
    "Строка ввода"
)

replace_once(
    '''        <button
          className="nexus-console-send"''',
    '''        <button
          className={`nexus-console-mic ${listening ? "listening" : ""}`}
          onClick={() => void listenCommand()}
          disabled={busy || !!pending}
          title={listening ? "Слушаю..." : "Голосовая команда"}
          aria-label="Голосовая команда"
        >
          {listening ? <LoaderCircle size={17} className="nexus-spin" /> : <Mic size={17} />}
        </button>
        <button
          className="nexus-console-send"''',
    "Кнопка микрофона"
)

tsx.write_text(s, encoding="utf-8")

voice_css = '''

/* NEXUS CORE — голосовой ввод */
.nexus-console-mic {
  flex: 0 0 43px;
  width: 43px;
  min-width: 43px;
  height: 43px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.07);
  color: inherit;
  cursor: pointer;
  transition: background 160ms ease, border-color 160ms ease, transform 160ms ease;
}

.nexus-console-mic:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.3);
}

.nexus-console-mic:active:not(:disabled) {
  transform: scale(0.96);
}

.nexus-console-mic:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.nexus-console-mic.listening {
  color: #ffffff;
  background: rgba(220, 65, 65, 0.28);
  border-color: rgba(255, 100, 100, 0.65);
}
'''

current_css = css.read_text(encoding="utf-8")
if ".nexus-console-mic {" not in current_css:
    css.write_text(current_css.rstrip() + "\n" + voice_css, encoding="utf-8")

print("VOICE UI PATCH OK")
