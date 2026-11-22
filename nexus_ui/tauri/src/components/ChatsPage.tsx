import "./WorkspaceModules.css";
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Send, KeyRound, MessageSquare, Trash2, Lock, Users } from "lucide-react";

type Message = { role: string; content: string };
type History = Record<string, Message[]>;

type SubscriptionInfo = {
  plan: "free" | "titan";
  status: string;
  freeProvider: string | null;
};

const models: Record<string, string[]> = {
  openai: ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"],
  anthropic: ["claude-sonnet-4-5", "claude-haiku-4-5"],
  gemini: ["gemini-3.8-flash"],
  deepseek: ["deepseek-flash", "deepseek-v4-pro"],
  grok: ["grok-4.7"],
  mistral: ["mistral-small-latest"],
  qwen: ["qwen-plus-latest"]
};

const labels: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  gemini: "Google Gemini",
  deepseek: "DeepSeek",
  grok: "Grok",
  mistral: "Le Chat (Mistral)",
  qwen: "Qwen"
};

const providers = Object.keys(models);

export default function ChatsPage() {
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState(models.openai[0]);
  const [subscription, setSubscription] = useState<SubscriptionInfo>({
    plan: "free", status: "active", freeProvider: null
  });
  const [key, setKey] = useState("");
  const [hasKey, setHasKey] = useState(false);
  const [history, setHistory] = useState<History>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [choosing, setChoosing] = useState(false);
  const [multiMode, setMultiMode] = useState(false);
  const [selectedProviders, setSelectedProviders] = useState<string[]>(["openai"]);
  const [demoMode, setDemoMode] = useState(false);
  const [demoResults, setDemoResults] = useState<Record<string, string>>({});

  const messages = history[provider] ?? [];
  const isTitan = subscription.plan === "titan";
  const isLocked = !isTitan && subscription.freeProvider !== null;
  const canUseCurrent = isTitan || subscription.freeProvider === provider;

  async function refreshKey(p = provider) {
    if (!isTitan && subscription.freeProvider !== p) {
      setHasKey(false);
      return;
    }
    try {
      setHasKey(await invoke<boolean>("provider_key_status", { provider: p }));
    } catch (e) {
      setNotice(String(e));
    }
  }

  useEffect(() => {
    void invoke<SubscriptionInfo>("get_subscription")
      .then(data => {
        setSubscription(data);
        if (data.plan === "free" && data.freeProvider) {
          setProvider(data.freeProvider);
          setSelectedProviders([data.freeProvider]);
        }
      })
      .catch(e => setNotice(String(e)));

    void invoke<History>("load_chat_history")
      .then(data => setHistory(data && typeof data === "object" && !Array.isArray(data) ? data : {}))
      .catch(e => setNotice(String(e)));
  }, []);

  useEffect(() => {
    setModel(models[provider][0]);
    if (isTitan || subscription.freeProvider === provider) {
      void refreshKey(provider);
    } else {
      setHasKey(false);
    }
  }, [provider, subscription.plan, subscription.freeProvider]);

  function toggleProvider(p: string) {
    setSelectedProviders(current => {
      if (current.includes(p)) {
        return current.filter(item => item !== p);
      }
      if (current.length >= 4) {
        setNotice("В Multi-AI можно выбрать не более четырёх провайдеров.");
        return current;
      }
      return [...current, p];
    });
  }

  function toggleMultiMode() {
    if (!isTitan) {
      setNotice("Режим Multi-AI доступен в NEXUS TITAN.");
      return;
    }
    if (!multiMode && selectedProviders.length === 0) {
      setSelectedProviders([provider]);
    }
    setMultiMode(value => !value);
    setNotice("");
  }

  async function confirmProvider() {
    if (isLocked || choosing) return;
    setChoosing(true);
    try {
      const result = await invoke<SubscriptionInfo>("choose_free_provider", { provider });
      setSubscription(result);
      setNotice(`Выбран ${labels[provider]}. В FREE изменить провайдера уже нельзя.`);
    } catch (e) {
      setNotice(String(e));
    } finally {
      setChoosing(false);
    }
  }

  async function saveKey() {
    if (!canUseCurrent) {
      setNotice("Сначала подтверди выбор единственного AI-провайдера.");
      return;
    }
    try {
      await invoke("save_provider_key", { provider, key });
      setKey("");
      setHasKey(true);
      setNotice("API-ключ сохранён в защищённом хранилище Windows.");
    } catch (e) {
      setNotice(String(e));
    }
  }

  async function deleteKey() {
    try {
      await invoke("delete_provider_key", { provider });
      setHasKey(false);
      setKey("");
      setNotice("Ключ удалён.");
    } catch (e) {
      setNotice(String(e));
    }
  }

  async function persist(next: History) {
    setHistory(next);
    try {
      await invoke("save_chat_history", { history: next });
    } catch (e) {
      setNotice(String(e));
    }
  }

  function toggleDemoMode() {
    setDemoMode(value => !value);
    setDemoResults({});
    setNotice("Демонстрационный режим не отправляет запросы и не изменяет историю чатов.");
  }

  async function sendMulti(text: string) {
    if (!isTitan) {
      setNotice("Multi-AI доступен только в TITAN.");
      return;
    }
    if (selectedProviders.length === 0) {
      setNotice("Выбери хотя бы одного AI-провайдера.");
      return;
    }

    if (demoMode) {
      const results: Record<string, string> = {};
      for (const p of selectedProviders) {
        results[p] = `Это демонстрационный ответ ${labels[p]}.

Получено тестовое сообщение:
«${text}»

Интерфейс Multi-AI работает. Реальный ответ появится после подключения API-ключа.`;
      }
      setDemoResults(results);
      setInput("");
      setNotice("Демонстрация завершена. Реальные AI-запросы не выполнялись.");
      return;
    }

    setBusy(true);
    setInput("");
    setNotice("");

    const initial: History = { ...history };
    for (const p of selectedProviders) {
      initial[p] = [...(history[p] ?? []), { role: "user", content: text }];
    }
    setHistory(initial);

    try {
      const results = await Promise.all(
        selectedProviders.map(async p => {
          const conversation = initial[p];

          try {
            const keyAvailable = await invoke<boolean>("provider_key_status", {
              provider: p
            });

            if (!keyAvailable) {
              throw new Error("API-ключ не настроен. Добавь его в подключении провайдера.");
            }

            const answer = await invoke<string>("send_chat_message", {
              provider: p,
              model: models[p][0],
              messages: conversation.slice(-40)
            });

            return {
              provider: p,
              messages: [...conversation, { role: "assistant", content: answer }]
            };
          } catch (error) {
            return {
              provider: p,
              messages: [
                ...conversation,
                { role: "assistant", content: `Ошибка: ${String(error)}` }
              ]
            };
          }
        })
      );

      const completed: History = { ...initial };
      for (const result of results) {
        completed[result.provider] = result.messages;
      }
      await persist(completed);
    } finally {
      setBusy(false);
    }
  }

  async function send() {
    const text = input.trim();
    if (!text || busy) return;

    if (multiMode) {
      await sendMulti(text);
      return;
    }

    if (!canUseCurrent) {
      setNotice("Сначала подтверди выбор AI-провайдера.");
      return;
    }
    if (!hasKey) {
      setNotice("Сначала добавь API-ключ провайдера.");
      return;
    }

    const next = [...messages, { role: "user", content: text }];
    const updated = { ...history, [provider]: next };
    setInput("");
    setBusy(true);
    setHistory(updated);

    try {
      const answer = await invoke<string>("send_chat_message", {
        provider, model, messages: next.slice(-40)
      });
      const completed = {
        ...updated,
        [provider]: [...next, { role: "assistant", content: answer }]
      };
      await persist(completed);
    } catch (e) {
      setNotice(String(e));
      await persist(updated);
    } finally {
      setBusy(false);
    }
  }

  async function clearChat() {
    if (demoMode) {
      setDemoResults({});
      setNotice("Демонстрационные ответы очищены. История чатов не изменена.");
      return;
    }
    const next = { ...history };
    const targets = multiMode ? selectedProviders : [provider];
    for (const p of targets) next[p] = [];
    await persist(next);
  }

  return <div className="module-page chats-page">
    <div className="module-page-heading">
      <div>
        <span className="module-eyebrow">AI CONNECTIONS</span>
        <h1>Чаты</h1>
        <p>Общайся с нейросетями через собственные API-подключения.</p>
      </div>
    </div>

    <div className="module-notice">
      {isTitan
        ? "NEXUS TITAN · Все доступные AI-провайдеры открыты."
        : isLocked
          ? `NEXUS FREE · Закреплённый провайдер: ${labels[subscription.freeProvider!]}. Изменить выбор можно только с TITAN.`
          : "NEXUS FREE · Ты можешь выбрать любого одного AI-провайдера. Подтвердить выбор можно только один раз — после этого заменить его в FREE будет невозможно."}
    </div>

    {notice && <div className="module-notice">{notice}</div>}

    <div className="module-panel">
      <h2><KeyRound size={18}/> Подключение провайдера</h2>

      <div className="chat-settings">
        <select
          className="module-input"
          value={provider}
          disabled={isLocked}
          onChange={e => setProvider(e.target.value)}
        >
          {providers.map(p =>
            <option value={p} key={p}>{labels[p]}</option>
          )}
        </select>

        <select
          className="module-input"
          value={model}
          onChange={e => setModel(e.target.value)}
        >
          {models[provider].map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>

      {!isTitan && !isLocked && (
        <button
          className="module-primary"
          disabled={choosing}
          onClick={() => void confirmProvider()}
        >
          <Lock size={15}/>
          {choosing ? "Сохраняем выбор..." : `Подтвердить выбор: ${labels[provider]}`}
        </button>
      )}

      <div className="chat-key-row">
        <input
          className="module-input"
          type="password"
          autoComplete="off"
          placeholder={hasKey ? "Ключ сохранён — можно заменить" : "Вставь API-ключ"}
          value={key}
          disabled={!canUseCurrent}
          onChange={e => setKey(e.target.value)}
        />
        <button
          className="module-primary"
          disabled={!canUseCurrent || !key.trim()}
          onClick={() => void saveKey()}
        >
          Сохранить ключ
        </button>
        {hasKey && (
          <button className="module-quiet" onClick={() => void deleteKey()}>
            <Trash2 size={15}/> Удалить
          </button>
        )}
      </div>

      <small className="module-hint">
        {hasKey
          ? "Ключ хранится в Windows Credential Manager."
          : "Ключ не сохраняется в истории чатов или обычных файлах приложения."}
      </small>
    </div>

    <div className="module-panel chat-multi-panel">
      <div className="chat-multi-heading">
        <h2><Users size={18}/> Режим общения</h2>
        <button
          className={`module-primary ${multiMode ? "chat-mode-active" : ""}`}
          disabled={!isTitan}
          onClick={toggleMultiMode}
        >
          {multiMode ? "Включён Multi-AI" : "Включить Multi-AI"}
        </button>
      </div>

      {!isTitan ? (
        <small className="module-hint">Параллельное общение с несколькими AI доступно в TITAN.</small>
      ) : (
        <>
          <p className="chat-multi-description">
            Выбери до четырёх нейросетей. Одно сообщение будет отправлено всем выбранным одновременно.
          </p>
          <div className="chat-provider-grid">
            {providers.map(p => (
              <label className="chat-provider-option" key={p}>
                <input
                  type="checkbox"
                  checked={selectedProviders.includes(p)}
                  disabled={!selectedProviders.includes(p) && selectedProviders.length >= 4}
                  onChange={() => toggleProvider(p)}
                />
                <span>{labels[p]}</span>
              </label>
            ))}
          </div>
          <small className="module-hint">
            Выбрано: {selectedProviders.length} / 4
          </small>
          <div style={{ marginTop: 14 }}>
            <button className="module-quiet" onClick={toggleDemoMode}>
              {demoMode ? "Выключить демонстрацию" : "Включить демонстрацию без API-ключей"}
            </button>
            {demoMode && (
              <small className="module-hint" style={{ display: "block", marginTop: 9 }}>
                ДЕМО-РЕЖИМ · Ответы тестовые, запросы к AI не отправляются.
              </small>
            )}
          </div>
        </>
      )}
    </div>

    <div className="module-chat-window">
      <div className="module-toolbar">
        <span>
          <MessageSquare size={15}/>
          {multiMode
            ? `Параллельный диалог · ${selectedProviders.length} AI`
            : `Диалог · ${labels[provider]} / ${model}`}
        </span>
        <button className="module-quiet" onClick={() => void clearChat()}>
          <Trash2 size={14}/> Очистить
        </button>
      </div>

      {multiMode ? (
        <div className="chat-multi-results">
          {selectedProviders.map(p => {
            const providerMessages = history[p] ?? [];
            return (
              <section className="chat-ai-card" key={p}>
                <div className="chat-ai-card-heading">
                  <strong>{labels[p]}</strong>
                  <small>{models[p][0]}</small>
                </div>
                <div className="chat-ai-card-messages">
                  {demoMode ? (
                    demoResults[p]
                      ? <div className="chat-demo-answer">
                          <small>ДЕМОНСТРАЦИОННЫЙ ОТВЕТ · НЕ ОТ AI</small>
                          <p>{demoResults[p]}</p>
                        </div>
                      : <div className="chat-ai-empty">Отправь сообщение для демонстрации</div>
                  ) : providerMessages.length === 0
                    ? <div className="chat-ai-empty">Ответы появятся здесь</div>
                    : providerMessages.map((m, i) => (
                        <div className={`chat-bubble ${m.role}`} key={i}>
                          <small>{m.role === "user" ? "ВЫ" : labels[p].toUpperCase()}</small>
                          <p>{m.content}</p>
                        </div>
                      ))}
                  {busy && providerMessages[providerMessages.length - 1]?.role === "user" && (
                    <div className="chat-bubble assistant">
                      <small>{labels[p].toUpperCase()}</small>
                      <p>Ответ готовится…</p>
                    </div>
                  )}
                </div>
              </section>
            );
          })}
        </div>
      ) : (
        <div className="module-chat-messages">
          {messages.length === 0
            ? <div className="module-empty">
                <MessageSquare size={30}/>
                <h2>Начни диалог</h2>
                <p>Сообщения будут сохраняться локально на этом компьютере.</p>
              </div>
            : messages.map((m, i) =>
                <div className={`chat-bubble ${m.role}`} key={i}>
                  <small>{m.role === "user" ? "ВЫ" : labels[provider].toUpperCase()}</small>
                  <p>{m.content}</p>
                </div>
              )}
          {busy && <div className="chat-bubble assistant">
            <small>{labels[provider].toUpperCase()}</small>
            <p>Ответ готовится…</p>
          </div>}
        </div>
      )}

      <div className="module-chat-compose">
        <textarea
          className="module-input"
          rows={2}
          placeholder={multiMode ? "Сообщение для выбранных AI..." : "Напиши сообщение..."}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
        />
        <button
          className="module-primary"
          disabled={
            busy ||
            !input.trim() ||
            (multiMode ? selectedProviders.length === 0 : !canUseCurrent)
          }
          onClick={() => void send()}
        >
          <Send size={17}/> {busy ? "Ожидай..." : "Отправить"}
        </button>
      </div>
    </div>
  </div>;
}

