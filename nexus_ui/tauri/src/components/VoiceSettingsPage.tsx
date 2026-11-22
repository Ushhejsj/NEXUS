
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import {
  Volume2,
  Play,
  AudioLines,
  Crown,
  Upload,
} from "lucide-react";
import { useSubscriptionStore } from "../stores/subscription";

type VoiceOption = {
  id: string;
  name: string;
};

type VoiceSettings = {
  voiceId: string | null;
  rate: number;
  volume: number;
};

export default function VoiceSettingsPage() {
  const plan = useSubscriptionStore(state => state.plan);
  const isTitan = plan === "titan";

  const [voices, setVoices] = useState<VoiceOption[]>([]);
  const [settings, setSettings] = useState<VoiceSettings>({
    voiceId: null,
    rate: 185,
    volume: 1,
  });
  const [loading, setLoading] = useState(true);
  const [speaking, setSpeaking] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [voiceResult, savedSettings] = await Promise.all([
          invoke<{ voices: VoiceOption[] }>("list_voice_options"),
          invoke<VoiceSettings>("get_voice_settings"),
        ]);

        if (!active) return;

        setVoices(voiceResult.voices ?? []);
        setSettings({
          voiceId: savedSettings.voiceId ?? null,
          rate: savedSettings.rate ?? 185,
          volume: savedSettings.volume ?? 1,
        });
      } catch (e) {
        if (active) setError(String(e));
      } finally {
        if (active) setLoading(false);
      }
    }

    load();
    return () => {
      active = false;
    };
  }, []);

  async function updateSettings(next: VoiceSettings) {
    setSettings(next);
    setError("");
    setSaved(false);

    try {
      const result = await invoke<VoiceSettings>(
        "save_voice_settings",
        { settings: next }
      );

      setSettings({
        voiceId: result.voiceId ?? null,
        rate: result.rate,
        volume: result.volume,
      });
      setSaved(true);
    } catch (e) {
      setError(String(e));
    }
  }

  async function addVoice() {
    if (!isTitan || importing) return;

    setImporting(true);
    setError("");

    try {
      const selected = await open({
        title: "Выберите файл голоса Piper",
        multiple: false,
        directory: false,
        filters: [{ name: "Голос Piper", extensions: ["onnx"] }],
      });

      if (typeof selected !== "string") return;

      const imported = await invoke<{ id: string; name: string }>(
        "import_voice_model",
        { sourcePath: selected }
      );

      const result = await invoke<{ voices: VoiceOption[] }>(
        "list_voice_options"
      );

      setVoices(result.voices ?? []);

      await updateSettings({
        ...settings,
        voiceId: imported.id,
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setImporting(false);
    }
  }

  async function testVoice() {
    setSpeaking(true);
    setError("");

    try {
      await invoke("nexus_core_speak", {
        text: "Здравствуйте! Это голосовой движок NEXUS. Проверка голосовых настроек.",
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setSpeaking(false);
    }
  }

  return (
    <div className="voice-settings">
      <header className="settings-page-heading">
        <span className="settings-overline">NEXUS VOICE SYSTEM</span>
        <h2>Голос NEXUS</h2>
        <p>
          Настройте голос, которым NEXUS говорит и озвучивает уведомления.
        </p>
      </header>

      <section className="settings-card">
        <div className="settings-card-heading">
          <div>
            <Volume2 size={17} />
            <h3>Настройки голоса</h3>
          </div>
          <small>SYSTEM TTS</small>
        </div>

        {loading ? (
          <p className="settings-hint">Загружаем голосовые настройки...</p>
        ) : (
          <>
            <div className="voice-control-row">
              <label htmlFor="nexus-voice-select">Голос</label>
              <select
                id="nexus-voice-select"
                value={settings.voiceId ?? ""}
                disabled={!isTitan}
                onChange={e =>
                  updateSettings({
                    ...settings,
                    voiceId: e.target.value || null,
                  })
                }
              >
                <option value="">Голос Denis (по умолчанию)</option>
                {voices.map(voice => (
                  <option key={voice.id} value={voice.id}>
                    {voice.name}
                  </option>
                ))}
              </select>
            </div>

            {!isTitan && (
              <div className="voice-plan-note">
                <Crown size={15} />
                <span>
                  Выбор других голосов доступен в NEXUS TITAN.
                  Голос Denis доступен в FREE.
                </span>
              </div>
            )}

            <div className="voice-control-row">
              <label htmlFor="nexus-voice-rate">
                Скорость речи
                <strong>{settings.rate}</strong>
              </label>
              <input
                id="nexus-voice-rate"
                type="range"
                min="100"
                max="300"
                step="5"
                value={settings.rate}
                onChange={e =>
                  updateSettings({
                    ...settings,
                    rate: Number(e.target.value),
                  })
                }
              />
            </div>

            <div className="voice-control-row">
              <label htmlFor="nexus-voice-volume">
                Громкость
                <strong>{Math.round(settings.volume * 100)}%</strong>
              </label>
              <input
                id="nexus-voice-volume"
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.volume}
                onChange={e =>
                  updateSettings({
                    ...settings,
                    volume: Number(e.target.value),
                  })
                }
              />
            </div>

            <div className="voice-test-row">
              <button
                className="voice-test-button"
                onClick={testVoice}
                disabled={speaking}
              >
                {speaking ? (
                  <AudioLines size={16} />
                ) : (
                  <Play size={16} />
                )}
                {speaking ? "Воспроизводится..." : "Проверить голос"}
              </button>

              {saved && (
                <span className="voice-saved">Настройки сохранены</span>
              )}
            </div>
          </>
        )}

        {error && <p className="voice-error">{error}</p>}
      </section>

      <section className="settings-card">
        <div className="settings-card-heading">
          <div>
            <AudioLines size={17} />
            <h3>Дополнительные голоса</h3>
          </div>
          <small>VOICE LIBRARY</small>
        </div>

        {isTitan ? (
          <>
            <p className="settings-hint">
              Импортируйте дополнительные голоса Piper в приложение.
              Для файла модели .onnx рядом должен находиться файл
              конфигурации .onnx.json.
            </p>

            <button
              className="voice-import-button"
              onClick={addVoice}
              disabled={importing}
            >
              <Upload size={16} />
              {importing ? "Импортируем голос..." : "Импортировать голос"}
            </button>

            <p className="voice-import-note">
              Импортируйте только те голоса, на использование которых
              у вас есть разрешение.
            </p>
          </>
        ) : (
          <div className="voice-plan-note">
            <Crown size={15} />
            <span>
              Дополнительные голоса доступны в NEXUS TITAN.
              Голос Denis остаётся базовым голосом FREE.
            </span>
          </div>
        )}
      </section>
    </div>
  );
}
