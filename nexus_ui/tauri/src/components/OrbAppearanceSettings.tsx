import { useOrbSettings, type OrbStyle, type OrbState } from "../stores/orbSettings";

const styles: OrbStyle[] = ["ENERGY", "PARTICLES", "HOLOGRAM", "FLUID", "VERITY"];
const states: OrbState[] = ["SLEEP", "WAKE_UP", "LISTENING", "THINKING", "EXECUTING"];

export default function OrbAppearanceSettings() {
  const style = useOrbSettings(s => s.style);
  const state = useOrbSettings(s => s.state);
  const primary = useOrbSettings(s => s.primary);
  const secondary = useOrbSettings(s => s.secondary);
  const glow = useOrbSettings(s => s.glow);
  const speed = useOrbSettings(s => s.speed);
  const scale = useOrbSettings(s => s.scale);
  const particleCount = useOrbSettings(s => s.particleCount);
  const set = useOrbSettings(s => s.set);

  return (
    <div className="orb-appearance-settings">
      <div className="settings-page-heading">
        <span className="settings-overline">NEXUS CORE / VISUAL ENGINE</span>
        <h2>Оформление орбов</h2>
        <p>Настройка внешнего вида и поведения визуального ядра</p>
      </div>

      <section className="settings-card">
        <div className="settings-card-heading">
          <div><span>01</span><h3>Стиль визуализации</h3></div>
          <small>ВЫБОР РЕЖИМА</small>
        </div>
        <div className="orb-style-grid">
          {styles.map(item => (
            <button
              key={item}
              className={style === item ? "selected" : ""}
              onClick={() => set({ style: item })}
            >
              <span className={`style-dot style-${item.toLowerCase()}`} />
              {item}
            </button>
          ))}
        </div>
      </section>

      <section className="settings-card">
        <div className="settings-card-heading">
          <div><span>02</span><h3>Цветовая палитра</h3></div>
          <small>МАТЕРИАЛЫ И СВЕЧЕНИЕ</small>
        </div>
        <div className="orb-color-row">
          <label htmlFor="orb-primary">Основной цвет</label>
          <input id="orb-primary" type="color" value={primary} onChange={e => set({ primary: e.target.value })} />
          <code>{primary.toUpperCase()}</code>
        </div>
        <div className="orb-color-row">
          <label htmlFor="orb-secondary">Дополнительный цвет</label>
          <input id="orb-secondary" type="color" value={secondary} onChange={e => set({ secondary: e.target.value })} />
          <code>{secondary.toUpperCase()}</code>
        </div>
      </section>

      <section className="settings-card">
        <div className="settings-card-heading">
          <div><span>03</span><h3>Анимация и параметры</h3></div>
          <small>ДИНАМИКА ЯДРА</small>
        </div>

        <div className="orb-range">
          <div><label>Свечение</label><output>{glow.toFixed(1)}</output></div>
          <input type="range" min="0" max="2" step=".1" value={glow} onChange={e => set({ glow: Number(e.target.value) })} />
        </div>
        <div className="orb-range">
          <div><label>Скорость анимации</label><output>{speed.toFixed(1)}×</output></div>
          <input type="range" min=".1" max="3" step=".1" value={speed} onChange={e => set({ speed: Number(e.target.value) })} />
        </div>
        <div className="orb-range">
          <div><label>Размер сферы</label><output>{scale.toFixed(2)}×</output></div>
          <input type="range" min=".5" max="1.5" step=".05" value={scale} onChange={e => set({ scale: Number(e.target.value) })} />
        </div>
        {style === "PARTICLES" && (
          <div className="orb-range">
            <div><label>Количество частиц</label><output>{particleCount}</output></div>
            <input type="range" min="10" max="260" step="5" value={particleCount} onChange={e => set({ particleCount: Number(e.target.value) })} />
          </div>
        )}
      </section>

      <section className="settings-card">
        <div className="settings-card-heading">
          <div><span>04</span><h3>Состояние ядра</h3></div>
          <small>ТЕСТ АНИМАЦИИ</small>
        </div>
        <div className="orb-state-controls settings-orb-states">
          {states.map(item => (
            <button
              key={item}
              className={state === item ? "selected" : ""}
              onClick={() => {
                set({ state: item });
                if (item === "WAKE_UP") {
                  window.setTimeout(() => {
                    if (useOrbSettings.getState().state === "WAKE_UP") {
                      set({ state: "LISTENING" });
                    }
                  }, 1100);
                }
              }}
            >
              {item.replace("_", " ")}
            </button>
          ))}
        </div>
        <p className="settings-hint">Изменения применяются непосредственно к орбу на главной странице.</p>
      </section>
    </div>
  );
}
