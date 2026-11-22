import { useState } from "react";
import {
  Palette, Orbit, LayoutDashboard, BrainCircuit, Crown, Volume2
} from "lucide-react";
import AppearanceSettings from "./AppearanceSettings";
import OrbAppearanceSettings from "./OrbAppearanceSettings";
import VoiceSettingsPage from "./VoiceSettingsPage";
import "./SettingsPage.css";

type Section = "appearance" | "orbs" | "voice" | "interface" | "ai" | "subscription";

const sections = [
  { id: "appearance" as const, label: "Оформление", description: "Тема, фон и шрифты", icon: Palette },
  { id: "orbs" as const, label: "Оформление орбов", description: "Внешний вид AI-ядер", icon: Orbit },
  { id: "voice" as const, label: "Голос NEXUS", description: "Речь и голосовые настройки", icon: Volume2 },
  { id: "interface" as const, label: "Интерфейс", description: "Расположение элементов", icon: LayoutDashboard },
  { id: "ai" as const, label: "AI и API", description: "Подключение нейросетей", icon: BrainCircuit },
  { id: "subscription" as const, label: "Подписка", description: "Дополнительные возможности", icon: Crown },
];

export default function SettingsPage() {
  const [section, setSection] = useState<Section>("appearance");

  return (
    <div className="settings-shell">
      <aside className="settings-sidebar">
        <div className="settings-sidebar-heading">НАСТРОЙКИ NEXUS</div>
        <nav>
          {sections.map(item => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`settings-nav-item ${section === item.id ? "active" : ""}`}
                onClick={() => setSection(item.id)}
              >
                <Icon size={17} strokeWidth={1.8} />
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="settings-section-content">
        {section === "appearance" && <AppearanceSettings />}
        {section === "orbs" && <OrbAppearanceSettings />}
        {section === "voice" && <VoiceSettingsPage />}
        {section === "interface" && (
          <div className="settings-placeholder">
            <LayoutDashboard size={25} />
            <span className="settings-overline">WORKSPACE CONFIGURATION</span>
            <h2>Интерфейс</h2>
            <p>Настройки расположения, видимости и поведения элементов появятся здесь.</p>
            <span className="settings-coming">РАЗДЕЛ ГОТОВИТСЯ</span>
          </div>
        )}
        {section === "ai" && (
          <div className="settings-placeholder">
            <BrainCircuit size={25} />
            <span className="settings-overline">AI CONNECTIONS</span>
            <h2>AI и API</h2>
            <p>Здесь будут настройки подключения нейросетей и управления API-ключами.</p>
            <span className="settings-coming">РАЗДЕЛ ГОТОВИТСЯ</span>
          </div>
        )}
        {section === "subscription" && (
          <div className="settings-placeholder">
            <Crown size={25} />
            <span className="settings-overline">NEXUS MEMBERSHIP</span>
            <h2>Подписка</h2>
            <p>Дополнительные возможности NEXUS появятся здесь в будущем.</p>
            <span className="settings-coming">СКОРО</span>
          </div>
        )}
      </main>
    </div>
  );
}
