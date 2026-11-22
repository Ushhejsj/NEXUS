import "./WorkspaceModules.css";
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { AppWindow, Plus, Play, Trash2, RefreshCw } from "lucide-react";

type AppEntry = { id: string; name: string; path: string };

export default function ApplicationsPage() {
  const [apps, setApps] = useState<AppEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  async function refresh() {
    try { setApps(await invoke<AppEntry[]>("list_applications")); }
    catch (e) { setNotice(String(e)); }
  }

  useEffect(() => { void refresh(); }, []);

  async function add() {
    const selected = await open({
      multiple: false,
      filters: [{ name: "Windows applications", extensions: ["exe"] }]
    });
    if (!selected || Array.isArray(selected)) return;
    setBusy(true);
    try {
      await invoke("add_application", { path: selected });
      setNotice("Приложение добавлено.");
      await refresh();
    } catch (e) { setNotice(String(e)); }
    finally { setBusy(false); }
  }

  async function launch(id: string) {
    try { await invoke("launch_application", { id }); setNotice("Приложение запущено."); }
    catch (e) { setNotice(String(e)); }
  }

  async function remove(id: string) {
    try {
      await invoke("remove_application", { id });
      await refresh();
      setNotice("Приложение удалено из списка.");
    } catch (e) { setNotice(String(e)); }
  }

  return <div className="module-page">
    <div className="module-page-heading">
      <div><span className="module-eyebrow">NEXUS WORKSPACE</span><h1>Приложения</h1>
        <p>Твои программы в одном рабочем пространстве.</p></div>
      <button className="module-primary" onClick={() => void add()} disabled={busy}>
        <Plus size={17}/> Добавить приложение
      </button>
    </div>
    {notice && <div className="module-notice">{notice}</div>}
    <div className="module-toolbar">
      <span>{apps.length} приложений</span>
      <button className="module-quiet" onClick={() => void refresh()}><RefreshCw size={15}/> Обновить</button>
    </div>
    {apps.length === 0 ? <div className="module-empty">
      <AppWindow size={34}/><h2>Пока нет приложений</h2>
      <p>Добавь EXE-файлы программ, которыми пользуешься.</p>
      <button className="module-primary" onClick={() => void add()}><Plus size={16}/> Добавить первое приложение</button>
    </div> : <div className="module-list">
      {apps.map(app => <div className="module-item" key={app.id}>
        <div className="module-item-icon"><AppWindow size={21}/></div>
        <div className="module-item-copy"><strong>{app.name}</strong><small>{app.path}</small></div>
        <button className="module-icon-button" title="Запустить" onClick={() => void launch(app.id)}><Play size={17}/></button>
        <button className="module-icon-button danger" title="Удалить" onClick={() => void remove(app.id)}><Trash2 size={17}/></button>
      </div>)}
    </div>}
  </div>;
}

