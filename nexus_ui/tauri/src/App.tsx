import { useState, useEffect, lazy, Suspense } from "react";
import SettingsPage from "./components/SettingsPage";
import ApplicationsPage from "./components/ApplicationsPage";
import MacrosPage from "./components/MacrosPage";
import ChatsPage from "./components/ChatsPage";
import NexusConsole from "./components/NexusConsole";
import SubscriptionPage from "./components/SubscriptionPage";
import { useApplyAppearance } from "./components/AppearanceSettings";
import { useSubscriptionStore } from "./stores/subscription";
const OrbPanel = lazy(() => import("./components/OrbPanel"));
const OrbLab = lazy(() => import("./components/OrbLab"));
import {
  Home,
  AppWindow,
  Workflow,
  MessageSquare,
  Settings,
  Plus,
  Sparkles,
  PanelLeftClose,
  PanelLeftOpen,
  Minus,
  Square,
  X,
  ChevronRight,
  Cpu,
  Activity,
  Orbit,
} from "lucide-react";
import { getCurrentWindow } from "@tauri-apps/api/window";

const navigation = [
  { id: "home", label: "Главная", icon: Home, description: "Центр управления NEXUS" },
  { id: "applications", label: "Приложения", icon: AppWindow, description: "Подключённые приложения и инструменты" },
  { id: "macros", label: "Макросы", icon: Workflow, description: "Автоматизация повседневных задач" },
  { id: "chats", label: "Чаты", icon: MessageSquare, description: "Общение с нейросетями" },
  { id: "settings", label: "Настройки", icon: Settings, description: "Персонализация и параметры системы" },
  { id: "orb-lab", label: "Orb Lab", icon: Orbit, description: "Экспериментальная графическая лаборатория" }
];

const appWindow = getCurrentWindow();

export default function App() {
  useApplyAppearance();
  const hydrateSubscription = useSubscriptionStore((state) => state.hydrate);
  useEffect(() => { void hydrateSubscription(); }, [hydrateSubscription]);
  const [active, setActive] = useState("home");
  const [collapsed, setCollapsed] = useState(false);

  const current = navigation.find((item) => item.id === active) ?? navigation[0];

  return (
    <div className={`nexus-app ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="brand-row">
            <div className="brand">
              <div className="brand-icon"><Sparkles size={19} strokeWidth={1.8} /></div>
              {!collapsed && <span className="brand-name">NEXUS</span>}
            </div>
            <button
              className="collapse-button"
              title={collapsed ? "Развернуть панель" : "Свернуть панель"}
              onClick={() => setCollapsed((value) => !value)}
            >
              {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
            </button>
          </div>

          {!collapsed && <div className="workspace-label">РАБОЧЕЕ ПРОСТРАНСТВО</div>}

          <nav className="navigation">
            {navigation.map((item) => {
              const Icon = item.icon;
              const selected = active === item.id;

              return (
                <button
                  key={item.id}
                  className={`nav-item ${selected ? "active" : ""}`}
                  onClick={() => setActive(item.id)}
                  title={collapsed ? item.label : undefined}
                  aria-current={selected ? "page" : undefined}
                >
                  <span className="nav-icon"><Icon size={18} strokeWidth={1.8} /></span>
                  {!collapsed && <span className="nav-label">{item.label}</span>}
                  {selected && <span className="active-indicator" />}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="sidebar-bottom">
          <button
            className="subscription-button"
            title={collapsed ? "Подписка" : undefined}
            onClick={() => setActive("subscription")}
          >
            <span className="subscription-icon"><Plus size={17} /></span>
            {!collapsed && <span>Подписка</span>}

          </button>

          <div className="profile">
            <div className="profile-avatar">N</div>
            {!collapsed && (
              <div className="profile-info">
                <div className="profile-name">NEXUS User</div>
                <div className="profile-status"><span /> Локальная система</div>
              </div>
            )}
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="titlebar">
          <div className="titlebar-left" data-tauri-drag-region>
            <span className="titlebar-section">{current.label}</span>
            <ChevronRight size={13} className="titlebar-chevron" />
            <span className="titlebar-context">NEXUS Workspace</span>
          </div>

          <div className="titlebar-actions">
            <div className="system-indicator"><span /> SYSTEM</div>
            <div className="window-controls">
              <button title="Свернуть" onClick={() => void appWindow.minimize()}>
                <Minus size={14} />
              </button>
              <button title="Развернуть" onClick={() => void appWindow.toggleMaximize()}>
                <Square size={12} />
              </button>
              <button className="close-window" title="Закрыть" onClick={() => void appWindow.close()}>
                <X size={15} />
              </button>
            </div>
          </div>
        </header>

        <section className="page-content">
          {active === "home" ? (
            <>
              <div className="page-heading">
                <div className="eyebrow"><span className="eyebrow-line" /> PERSONAL AI SYSTEM</div>
                <h1>Добро пожаловать в <span>NEXUS</span></h1>
                <p className="page-description">
                  Единое пространство для приложений, автоматизации и искусственного интеллекта.
                </p>
              </div>

              <Suspense fallback={<div style={{ minHeight: 360, display: "grid", placeItems: "center", color: "#888397", fontSize: 12, letterSpacing: 2 }}>ЗАГРУЗКА ВИЗУАЛЬНОГО ЯДРА</div>}><OrbPanel /></Suspense>
              <NexusConsole />

              <div className="welcome-card">
                <div className="welcome-orb"><Sparkles size={25} strokeWidth={1.5} /></div>
                <div className="welcome-copy">
                  <div className="card-overline">NEXUS CORE</div>
                  <h2>Система готова к настройке</h2>
                  <p>Локальное интеллектуальное ядро подключено. Управляйте системой через орб и консоль NEXUS.</p>
                </div>
                <div className="card-decoration"><Cpu size={104} strokeWidth={0.7} /></div>
              </div>

              <div className="section-heading">
                <div>
                  <div className="eyebrow">OVERVIEW</div>
                  <h2>Рабочее пространство</h2>
                </div>
                <span className="section-caption">ОСНОВНЫЕ МОДУЛИ</span>
              </div>

              <div className="module-grid">
                <button className="module-card" onClick={() => setActive("applications")}>
                  <span className="module-icon"><AppWindow size={19} /></span>
                  <span className="module-title">Приложения</span>
                  <span className="module-description">Управление подключениями</span>
                  <ChevronRight className="module-arrow" size={16} />
                </button>
                <button className="module-card" onClick={() => setActive("macros")}>
                  <span className="module-icon"><Workflow size={19} /></span>
                  <span className="module-title">Макросы</span>
                  <span className="module-description">Сценарии автоматизации</span>
                  <ChevronRight className="module-arrow" size={16} />
                </button>
                <button className="module-card" onClick={() => setActive("chats")}>
                  <span className="module-icon"><MessageSquare size={19} /></span>
                  <span className="module-title">AI Чаты</span>
                  <span className="module-description">Подключение нейросетей</span>
                  <ChevronRight className="module-arrow" size={16} />
                </button>
              </div>

              <div className="system-footer">
                <div><Activity size={14} /> NEXUS ENVIRONMENT</div>
                <span>DESKTOP INTERFACE</span>
              </div>
            </>
          ) : active === "applications" ? (
            <ApplicationsPage />
          ) : active === "macros" ? (
            <MacrosPage />
          ) : active === "chats" ? (
            <ChatsPage />
          ) : active === "settings" ? (
            <SettingsPage />
          ) : active === "orb-lab" ? (
            <Suspense fallback={<div style={{ padding: 30, color: "#888397" }}>Загрузка лаборатории...</div>}><OrbLab /></Suspense>
          ) : active === "subscription" ? (
            <SubscriptionPage />
          ) : (
            <div className="placeholder-page">
              <div className="placeholder-icon">
                {(() => {
                  const Icon = current.icon;
                  return <Icon size={25} strokeWidth={1.6} />;
                })()}
              </div>
              <div className="eyebrow">NEXUS WORKSPACE</div>
              <h1>{current.label}</h1>
              <p className="page-description">{current.description}. Функциональность будет подключена на следующих этапах.</p>
              <span className="status-pill">МОДУЛЬ ГОТОВИТСЯ</span>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}












