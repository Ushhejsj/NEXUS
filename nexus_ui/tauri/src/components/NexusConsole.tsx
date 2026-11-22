import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Send, Mic, MicOff, Cpu, ShieldCheck, X, LoaderCircle, AlertCircle } from "lucide-react";
import "./NexusConsole.css";

type CoreResponse = {
  status?: string;
  ollama?: boolean;
  model?: string;
  cached_apps?: number;
  speech?: string;
  execution_log?: string[];
  confirmation_prompt?: string;
  token?: string;
  error?: string;
  text?: string;
};

type Message = {
  id: number;
  role: "user" | "assistant" | "system";
  text: string;
};

export default function NexusConsole() {
  const [command, setCommand] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, role: "assistant", text: "Локальное ядро NEXUS готово. Ожидаю команду." }
  ]);
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const listeningRef = useRef(false);
  const [status, setStatus] = useState<CoreResponse | null>(null);
  const [statusError, setStatusError] = useState("");
  const [pending, setPending] = useState<{ token: string; prompt: string } | null>(null);
  const sequence = useRef(2);
  const endRef = useRef<HTMLDivElement>(null);

  function addMessage(role: Message["role"], text: string) {
    setMessages((current) => [
      ...current,
      { id: sequence.current++, role, text }
    ]);
  }

  async function speakResponse(text: string) {
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
  }

  useEffect(() => {
    let mounted = true;

    invoke<CoreResponse>("nexus_core_status")
      .then((result) => {
        if (mounted) {
          setStatus(result);
          setStatusError("");
        }
      })
      .catch((error) => {
        if (mounted) setStatusError(String(error));
      });

    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, pending]);

  async function sendCommand() {
    const value = command.trim();
    if (!value || busy || pending) return;

    setCommand("");
    addMessage("user", value);
    setBusy(true);

    try {
      const response = await invoke<CoreResponse>("nexus_core_command", { text: value });

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
        await showResponse(response);
      }
    } catch (error) {
      addMessage("system", `Ошибка ядра: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function toggleVoice() {
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
  }

  async function resolveConfirmation(confirmed: boolean) {
    if (!pending || busy) return;

    const token = pending.token;
    setPending(null);
    setBusy(true);

    try {
      const response = confirmed
        ? await invoke<CoreResponse>("nexus_core_confirm", { token })
        : await invoke<CoreResponse>("nexus_core_cancel", { token });

      if (response.status === "cancelled") {
        const message = response.speech || "Выполнение отменено.";
        addMessage("assistant", message);
        await speakResponse(message);
      } else {
        await showResponse(response);
      }
    } catch (error) {
      addMessage("system", `Ошибка подтверждения: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  const online = status?.status === "online" && status.ollama === true;

  return (
    <section className="nexus-console">
      <div className="nexus-console-header">
        <div className="nexus-console-heading">
          <div className="nexus-console-icon"><Cpu size={17} /></div>
          <div>
            <div className="nexus-console-title">NEXUS CORE</div>
            <div className="nexus-console-subtitle">Локальный интеллектуальный интерфейс</div>
          </div>
        </div>

        <div className={`nexus-core-status ${online ? "online" : "offline"}`}>
          <span />
          {online ? "ЯДРО В СЕТИ" : statusError ? "НЕТ СОЕДИНЕНИЯ" : "ПРОВЕРКА ЯДРА"}
        </div>
      </div>

      {statusError && (
        <div className="nexus-console-warning">
          <AlertCircle size={14} />
          <span>{statusError}</span>
        </div>
      )}

      {status && (
        <div className="nexus-console-meta">
          {status.model && <span>МОДЕЛЬ: {status.model}</span>}
          {typeof status.cached_apps === "number" && <span>ПРИЛОЖЕНИЙ: {status.cached_apps}</span>}
          {status.ollama === false && <span className="nexus-console-meta-error">OLLAMA НЕ ЗАПУЩЕНА</span>}
        </div>
      )}

      <div className="nexus-console-messages" aria-live="polite">
        {messages.map((message) => (
          <div key={message.id} className={`nexus-console-message ${message.role}`}>
            {message.role === "assistant" && <span className="message-mark"><Cpu size={13} /></span>}
            <div className="message-content">{message.text}</div>
          </div>
        ))}
        {busy && (
          <div className="nexus-console-loading">
            <LoaderCircle size={14} className="nexus-spin" />
            NEXUS обрабатывает запрос…
          </div>
        )}
        <div ref={endRef} />
      </div>

      {pending && (
        <div className="nexus-confirmation">
          <div className="nexus-confirmation-text">
            <ShieldCheck size={17} />
            <span>{pending.prompt}</span>
          </div>
          <div className="nexus-confirmation-actions">
            <button className="nexus-confirm-yes" onClick={() => resolveConfirmation(true)} disabled={busy}>
              Подтвердить
            </button>
            <button className="nexus-confirm-no" onClick={() => resolveConfirmation(false)} disabled={busy}>
              <X size={13} /> Отмена
            </button>
          </div>
        </div>
      )}

      <div className="nexus-console-input-row">
        <textarea
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void sendCommand();
            }
          }}
          placeholder={pending ? "Сначала разрешите или отмените действие…" : "Введите команду для NEXUS…"}
          disabled={busy || !!pending}
          rows={2}
        />
        <button
          className={`nexus-console-mic ${listening ? "listening" : ""}`}
          onClick={() => void toggleVoice()}
          disabled={!!pending || (busy && !listening)}
          title={listening ? "Остановить голосовое управление" : "Включить голосовое управление"}
          aria-label={listening ? "Остановить голосовое управление" : "Включить голосовое управление"}
        >
          {listening ? <MicOff size={17} /> : <Mic size={17} />}
        </button>
        <button
          className="nexus-console-send"
          onClick={() => void sendCommand()}
          disabled={busy || !!pending || !command.trim()}
          title="Отправить команду"
        >
          {busy ? <LoaderCircle size={17} className="nexus-spin" /> : <Send size={17} />}
        </button>
      </div>
      <div className="nexus-console-hint">ENTER — отправить · SHIFT + ENTER — новая строка</div>
    </section>
  );
}