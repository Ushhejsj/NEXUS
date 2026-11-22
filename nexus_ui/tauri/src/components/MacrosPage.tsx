import "./WorkspaceModules.css";
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Plus, Play, Trash2, Workflow, Save } from "lucide-react";

type AppEntry = { id: string; name: string; path: string };
type Action = { kind: "launchApp"; appId: string } | { kind: "openUrl"; url: string } | { kind: "delay"; milliseconds: number };
type Macro = { id: string; name: string; actions: Action[] };

export default function MacrosPage() {
  const [macros, setMacros] = useState<Macro[]>([]);
  const [apps, setApps] = useState<AppEntry[]>([]);
  const [name, setName] = useState("");
  const [actions, setActions] = useState<Action[]>([]);
  const [kind, setKind] = useState("launchApp");
  const [appId, setAppId] = useState("");
  const [url, setUrl] = useState("https://");
  const [delay, setDelay] = useState("1000");
  const [notice, setNotice] = useState("");

  async function refresh() {
    try {
      const [m, a] = await Promise.all([
        invoke<Macro[]>("list_macros"), invoke<AppEntry[]>("list_applications")
      ]);
      setMacros(m); setApps(a);
    } catch (e) { setNotice(String(e)); }
  }
  useEffect(() => { void refresh(); }, []);

  function addAction() {
    if (kind === "launchApp") {
      if (!appId) { setNotice("Сначала добавь приложение во вкладке «Приложения»."); return; }
      setActions([...actions, { kind: "launchApp", appId }]);
    } else if (kind === "openUrl") {
      if (!url.startsWith("https://") && !url.startsWith("http://")) { setNotice("Укажи HTTP или HTTPS ссылку."); return; }
      setActions([...actions, { kind: "openUrl", url }]);
    } else {
      const ms = Number(delay);
      if (!Number.isFinite(ms) || ms < 0 || ms > 60000) { setNotice("Задержка: от 0 до 60000 мс."); return; }
      setActions([...actions, { kind: "delay", milliseconds: ms }]);
    }
    setNotice("");
  }

  async function save() {
    if (!name.trim() || !actions.length) { setNotice("Укажи название и добавь действия."); return; }
    const entry = { id: crypto.randomUUID(), name: name.trim(), actions };
    try {
      const updated = await invoke<Macro[]>("save_macro", { entry });
      setMacros(updated); setName(""); setActions([]); setNotice("Макрос сохранён.");
    } catch (e) { setNotice(String(e)); }
  }

  async function remove(id: string) {
    try { setMacros(await invoke<Macro[]>("delete_macro", { id })); }
    catch (e) { setNotice(String(e)); }
  }

  async function run(id: string) {
    try { await invoke("run_macro", { id }); setNotice("Макрос выполнен."); }
    catch (e) { setNotice(String(e)); }
  }

  function actionLabel(action: Action) {
    if (action.kind === "launchApp") return `Запустить: ${apps.find(a => a.id === action.appId)?.name ?? "приложение"}`;
    if (action.kind === "openUrl") return `Открыть: ${action.url}`;
    return `Пауза: ${action.milliseconds} мс`;
  }

  return <div className="module-page">
    <div className="module-page-heading"><div><span className="module-eyebrow">AUTOMATION CENTER</span><h1>Макросы</h1><p>Создавай последовательности действий и запускай их одним нажатием.</p></div></div>
    {notice && <div className="module-notice">{notice}</div>}
    <div className="module-panel">
      <h2><Plus size={18}/> Новый макрос</h2>
      <input className="module-input" placeholder="Название макроса" value={name} onChange={e => setName(e.target.value)}/>
      <div className="macro-builder">
        <select className="module-input" value={kind} onChange={e => setKind(e.target.value)}>
          <option value="launchApp">Запустить приложение</option><option value="openUrl">Открыть ссылку</option><option value="delay">Задержка</option>
        </select>
        {kind === "launchApp" && <select className="module-input" value={appId} onChange={e => setAppId(e.target.value)}>
          <option value="">Выбери приложение</option>{apps.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>}
        {kind === "openUrl" && <input className="module-input" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://example.com"/>}
        {kind === "delay" && <input className="module-input" type="number" min="0" max="60000" value={delay} onChange={e => setDelay(e.target.value)} placeholder="Миллисекунды"/>}
        <button className="module-quiet" onClick={addAction}><Plus size={16}/> Добавить действие</button>
      </div>
      {actions.length > 0 && <div className="macro-actions">{actions.map((a, i) => <div className="macro-action" key={i}>
        <span>{i + 1}</span>{actionLabel(a)}<button onClick={() => setActions(actions.filter((_, n) => n !== i))}>×</button>
      </div>)}</div>}
      <button className="module-primary" onClick={() => void save()}><Save size={16}/> Сохранить макрос</button>
    </div>
    <div className="module-toolbar"><span>Сохранённые макросы · {macros.length}</span></div>
    {macros.length === 0 ? <div className="module-empty"><Workflow size={32}/><h2>Макросов пока нет</h2><p>Создай первый сценарий автоматизации выше.</p></div> :
      <div className="module-list">{macros.map(m => <div className="module-item" key={m.id}>
        <div className="module-item-icon"><Workflow size={21}/></div>
        <div className="module-item-copy"><strong>{m.name}</strong><small>{m.actions.length} действий · {m.actions.map(actionLabel).join(" → ")}</small></div>
        <button className="module-icon-button" title="Запустить макрос" onClick={() => void run(m.id)}><Play size={17}/></button>
        <button className="module-icon-button danger" title="Удалить" onClick={() => void remove(m.id)}><Trash2 size={17}/></button>
      </div>)}</div>}
  </div>;
}

