from pathlib import Path
import shutil

bridge = Path("nexus_tauri_bridge.py")
tsx = Path("nexus_ui/tauri/src/components/NexusConsole.tsx")

p = bridge.read_text(encoding="utf-8")
t = tsx.read_text(encoding="utf-8")

shutil.copy2(bridge, bridge.with_suffix(".py.voice_backup"))
shutil.copy2(tsx, tsx.with_suffix(".tsx.voice_backup"))

old_timeout = '''    except sr.WaitTimeoutError:
        raise RuntimeError("Не услышал речь. Попробуйте ещё раз.")'''

new_timeout = '''    except sr.WaitTimeoutError:
        return {"status": "timeout"}'''

if p.count(old_timeout) != 1:
    raise RuntimeError("Не найден обработчик тайм-аута микрофона.")
p = p.replace(old_timeout, new_timeout, 1)

old_import = 'import { Send, Mic, Cpu, ShieldCheck, X, LoaderCircle, AlertCircle } from "lucide-react";'
new_import = 'import { Send, Mic, MicOff, Cpu, ShieldCheck, X, LoaderCircle, AlertCircle } from "lucide-react";'
if t.count(old_import) != 1:
    raise RuntimeError("Не найден импорт иконок.")
t = t.replace(old_import, new_import, 1)

old_state = '  const [listening, setListening] = useState(false);'
new_state = old_state + '\n  const listeningRef = useRef(false);'
if t.count(old_state) != 1:
    raise RuntimeError("Не найдено состояние listening.")
t = t.replace(old_state, new_state, 1)

start = t.index('  function speakResponse(text: string) {')
end = t.index('\n\n  useEffect(() => {', start)

new_speech = '''  async function speakResponse(text: string) {
    try {
      await invoke<CoreResponse>("nexus_core_speak", { text });
    } catch (error) {
      addMessage("system", `Ошибка озвучивания: ${String(error)}`);
    }
  }

  async function showResponse(response: CoreResponse) {
    if (response.speech) {
      addMessage("assistant", response.speech);
      await speakResponse(response.speech);
    }

    if (response.execution_log?.length) {
      response.execution_log.forEach((line) => addMessage("system", line));
    } else if (response.status === "submitted") {
      addMessage("system", "Команда передана исполнителю.");
    }
  }'''
t = t[:start] + new_speech + t[end:]

t = t.replace('        showResponse(response);', '        await showResponse(response);')
t = t.replace('        showResponse(response);', '        await showResponse(response);')

start = t.index('  async function listenCommand() {')
end = t.index('\n\n  async function resolveConfirmation', start)

new_loop = '''  async function toggleVoice() {
    if (listeningRef.current) {
      listeningRef.current = false;
      setListening(false);
      return;
    }

    if (busy || pending) return;

    listeningRef.current = true;
    setListening(true);
    setBusy(true);

    try {
      while (listeningRef.current) {
        const result = await invoke<CoreResponse>("nexus_core_listen");

        if (!listeningRef.current) break;

        // Обычная пауза между командами не выключает микрофон.
        if (result.status === "timeout") continue;

        const value = result.text?.trim();
        if (!value) continue;

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
            await speakResponse(response.speech);
          }

          // Для защищённых действий требуется явное подтверждение.
          listeningRef.current = false;
          setListening(false);
          break;
        }

        await showResponse(response);
      }
    } catch (error) {
      if (listeningRef.current) {
        addMessage("system", `Ошибка голосового управления: ${String(error)}`);
      }
    } finally {
      listeningRef.current = false;
      setListening(false);
      setBusy(false);
    }
  }'''
t = t[:start] + new_loop + t[end:]

t = t.replace(
    '        speakResponse(message);',
    '        await speakResponse(message);'
)

old_button = '''          onClick={() => void listenCommand()}
          disabled={busy || !!pending}
          title={listening ? "Слушаю..." : "Голосовая команда"}
          aria-label="Голосовая команда"
        >
          {listening ? <LoaderCircle size={17} className="nexus-spin" /> : <Mic size={17} />}'''

new_button = '''          onClick={() => void toggleVoice()}
          disabled={!!pending || (busy && !listening)}
          title={listening ? "Остановить голосовое управление" : "Включить голосовое управление"}
          aria-label={listening ? "Остановить голосовое управление" : "Включить голосовое управление"}
        >
          {listening ? <MicOff size={17} /> : <Mic size={17} />}'''

if t.count(old_button) != 1:
    raise RuntimeError("Не найден JSX кнопки микрофона.")

t = t.replace(old_button, new_button, 1)

bridge.write_text(p, encoding="utf-8")
tsx.write_text(t, encoding="utf-8")

print("CONTINUOUS VOICE MODE PATCH OK")
