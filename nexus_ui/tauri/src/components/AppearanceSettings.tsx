import { useEffect, useRef, useState } from "react";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  Sun, Moon, Monitor, Palette, Type, ImagePlus, Upload,
  SlidersHorizontal, Sparkles, RotateCcw, Check, X,
  Eye, Droplets, Layers, Settings2
} from "lucide-react";
import "./AppearanceSettings.css";
import WallpaperBrowser from "./WallpaperBrowser";

type Scheme = "dark" | "white" | "system";

type AppearanceState = {
  scheme: Scheme;
  accentColor: string;
  font: string;
  scale: number;
  backgroundImage: string;
  backgroundDim: number;
  backgroundBlur: number;
  liquidGlass: boolean;
  set: (values: Partial<AppearanceState>) => void;
  reset: () => void;
};

const defaults = {
  scheme: "dark" as Scheme,
  accentColor: "#9a8aff",
  font: "Inter",
  scale: 100,
  backgroundImage: "",
  backgroundDim: 25,
  backgroundBlur: 0,
  liquidGlass: false
};

const fontFamilyMap: Record<string, string> = {
  "Inter": "Inter",
  "Manrope": "Manrope Variable",
  "Onest": "Onest Variable",
  "Golos Text": "Golos Text Variable",
  "Montserrat": "Montserrat Variable",
  "Rubik": "Rubik Variable",
  "Nunito": "Nunito Variable",
  "Raleway": "Raleway Variable",
  "Comfortaa": "Comfortaa Variable",
  "Segoe UI": "Segoe UI"
};

const getFontFamily = (name: string) => fontFamilyMap[name] ?? name;
const useAppearance = create<AppearanceState>()(
  persist(
    (set) => ({
      ...defaults,
      set: (values) => set(values),
      reset: () => set(defaults)
    }),
    { name: "nexus-appearance-v1" }
  )
);

export function useApplyAppearance() {
  const appearance = useAppearance();

  const {
    scheme, accentColor, font, scale,
    backgroundImage, backgroundDim, backgroundBlur,
    liquidGlass
  } = appearance;

  useEffect(() => {
    const root = document.documentElement;

    const apply = () => {
      const systemLight = window.matchMedia("(prefers-color-scheme: light)").matches;
      const resolved = scheme === "system"
        ? (systemLight ? "white" : "dark")
        : scheme;

      root.dataset.scheme = resolved;
      root.dataset.liquidGlass = String(liquidGlass);

      root.style.setProperty("--nexus-accent", accentColor);
      root.style.setProperty("--color-accent", accentColor);

      const r = parseInt(accentColor.slice(1, 3), 16);
      const g = parseInt(accentColor.slice(3, 5), 16);
      const b = parseInt(accentColor.slice(5, 7), 16);

      root.style.setProperty("--nexus-accent-rgb", `${r}, ${g}, ${b}`);
      root.style.setProperty("--accent-rgb", `${r} ${g} ${b}`);
      root.style.setProperty("--nexus-font-family", `"${getFontFamily(font)}", "Segoe UI", sans-serif`);
      root.style.setProperty("--nexus-ui-scale", String(scale / 100));
      root.style.setProperty(
        "--nexus-wallpaper-image",
        backgroundImage ? `url("${backgroundImage}")` : "none"
      );
      root.style.setProperty("--nexus-wallpaper-dim", String(backgroundDim / 100));
      root.style.setProperty("--nexus-wallpaper-blur", `${backgroundBlur}px`);
    };

    apply();

    const media = window.matchMedia("(prefers-color-scheme: light)");
    media.addEventListener("change", apply);

    return () => media.removeEventListener("change", apply);
  }, [
    scheme, accentColor, font, scale,
    backgroundImage, backgroundDim, backgroundBlur, liquidGlass
  ]);
}
const palettes = [
  { name: "Фиолетовый", color: "#9a8aff" },
  { name: "Синий", color: "#529bff" },
  { name: "Голубой", color: "#35c9d5" },
  { name: "Изумрудный", color: "#35c98b" },
  { name: "Зелёный", color: "#8bcf54" },
  { name: "Золотой", color: "#e6b957" },
  { name: "Оранжевый", color: "#ff914d" },
  { name: "Красный", color: "#f05c75" },
  { name: "Розовый", color: "#ed79c5" },
  { name: "Белый", color: "#e5e5ed" }
];

const fonts = [
  "Inter", "Manrope", "Onest", "Golos Text",
  "Montserrat", "Rubik", "Nunito", "Raleway",
  "Comfortaa", "Segoe UI"
];

function SectionHeading({
  icon: Icon,
  title,
  description
}: {
  icon: typeof Palette;
  title: string;
  description: string;
}) {
  return (
    <div className="appearance-section-heading">
      <span className="appearance-section-icon"><Icon size={17} /></span>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function AppearanceSettings() {
  const appearance = useAppearance();
  const fileRef = useRef<HTMLInputElement>(null);
  const [notice, setNotice] = useState("");

  const {
    scheme, accentColor, font, scale,
    backgroundImage, backgroundDim, backgroundBlur,
    liquidGlass
  } = appearance;

  useEffect(() => {
    const root = document.documentElement;

    const apply = () => {
      const systemLight = window.matchMedia("(prefers-color-scheme: light)").matches;
      const resolved = scheme === "system"
        ? (systemLight ? "white" : "dark")
        : scheme;

      root.dataset.scheme = resolved;
      root.dataset.liquidGlass = String(liquidGlass);

      root.style.setProperty("--nexus-accent", accentColor);
      root.style.setProperty("--color-accent", accentColor);

      const r = parseInt(accentColor.slice(1, 3), 16);
      const g = parseInt(accentColor.slice(3, 5), 16);
      const b = parseInt(accentColor.slice(5, 7), 16);

      root.style.setProperty("--nexus-accent-rgb", `${r}, ${g}, ${b}`);
      root.style.setProperty("--accent-rgb", `${r} ${g} ${b}`);
      root.style.setProperty("--nexus-font-family", `"${getFontFamily(font)}", "Segoe UI", sans-serif`);
      root.style.setProperty("--nexus-ui-scale", String(scale / 100));
      root.style.setProperty(
        "--nexus-wallpaper-image",
        backgroundImage ? `url("${backgroundImage}")` : "none"
      );
      root.style.setProperty("--nexus-wallpaper-dim", String(backgroundDim / 100));
      root.style.setProperty("--nexus-wallpaper-blur", `${backgroundBlur}px`);
    };

    apply();

    const media = window.matchMedia("(prefers-color-scheme: light)");
    media.addEventListener("change", apply);

    return () => media.removeEventListener("change", apply);
  }, [
    scheme, accentColor, font, scale,
    backgroundImage, backgroundDim, backgroundBlur, liquidGlass
  ]);

  const chooseImage = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setNotice("Выбери файл изображения.");
      return;
    }

    if (file.size > 4 * 1024 * 1024) {
      setNotice("Файл слишком большой. Максимальный размер — 4 МБ.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      appearance.set({ backgroundImage: String(reader.result) });
      setNotice("Фоновое изображение установлено.");
    };
    reader.onerror = () => setNotice("Не удалось прочитать изображение.");
    reader.readAsDataURL(file);
    event.target.value = "";
  };

  return (
    <div className="appearance-settings">
      <div className="appearance-header">
        <div>
          <div className="appearance-eyebrow">
            <span /> ПЕРСОНАЛИЗАЦИЯ NEXUS
          </div>
          <h1>Оформление</h1>
          <p>Настрой внешний вид рабочего пространства.</p>
        </div>

        <button className="appearance-reset" onClick={() => {
          appearance.reset();
          setNotice("Настройки оформления сброшены.");
        }}>
          <RotateCcw size={14} />
          Сбросить
        </button>
      </div>

      {notice && (
        <div className="appearance-notice">
          <span>{notice}</span>
          <button onClick={() => setNotice("")} aria-label="Закрыть">
            <X size={14} />
          </button>
        </div>
      )}

      <div className="appearance-grid">
        <section className="appearance-card">
          <SectionHeading
            icon={Monitor}
            title="Цветовая схема"
            description="Выбери основное оформление приложения"
          />

          <div className="scheme-options">
            {([
              { id: "dark", label: "Тёмная", icon: Moon },
              { id: "white", label: "Светлая", icon: Sun },
              { id: "system", label: "Системная", icon: Monitor }
            ] as const).map((item) => {
              const Icon = item.icon;
              const selected = scheme === item.id;

              return (
                <button
                  key={item.id}
                  className={`scheme-option ${selected ? "selected" : ""}`}
                  onClick={() => appearance.set({ scheme: item.id })}
                >
                  <span className={`scheme-preview scheme-preview-${item.id}`}>
                    <span />
                    <span />
                    <span />
                  </span>
                  <span className="scheme-option-label">
                    <Icon size={14} /> {item.label}
                  </span>
                  {selected && <Check className="scheme-check" size={15} />}
                </button>
              );
            })}
          </div>
        </section>

        <section className="appearance-card">
          <SectionHeading
            icon={Palette}
            title="Акцентный цвет"
            description="Цвет выделения элементов интерфейса"
          />

          <div className="palette-grid">
            {palettes.map((item) => (
              <button
                key={item.color}
                className={`palette-swatch ${accentColor === item.color ? "selected" : ""}`}
                title={item.name}
                style={{ "--swatch": item.color } as React.CSSProperties}
                onClick={() => appearance.set({ accentColor: item.color })}
              >
                {accentColor === item.color && <Check size={15} />}
              </button>
            ))}
          </div>

          <div className="custom-color-row">
            <div>
              <strong>Свой цвет</strong>
              <span>{accentColor.toUpperCase()}</span>
            </div>
            <label className="color-picker-control" title="Выбрать цвет">
              <input
                type="color"
                value={accentColor}
                onChange={(event) => appearance.set({ accentColor: event.target.value })}
              />
              <span style={{ background: accentColor }} />
              <Palette size={14} />
            </label>
          </div>
        </section>

        <section className="appearance-card">
          <SectionHeading
            icon={Type}
            title="Шрифт интерфейса"
            description="Выбери гарнитуру для текстов и меню"
          />

          <div className="font-options">
            {fonts.map((item) => (
              <button
                key={item}
                className={`font-option ${font === item ? "selected" : ""}`}
                onClick={() => appearance.set({ font: item })}
              >
                <span style={{ fontFamily: `"${getFontFamily(item)}", sans-serif` }}>Aa</span>
                <span>{item}</span>
                {font === item && <Check size={14} />}
              </button>
            ))}
          </div>
        </section>

        <section className="appearance-card">
          <SectionHeading
            icon={SlidersHorizontal}
            title="Масштаб интерфейса"
            description="Размер элементов рабочего пространства"
          />

          <div className="scale-value">
            <strong>{scale}%</strong>
            <span>80–130%</span>
          </div>
          <input
            className="appearance-range"
            type="range"
            min="80"
            max="130"
            step="5"
            value={scale}
            onChange={(event) => appearance.set({ scale: Number(event.target.value) })}
          />
          <div className="range-labels"><span>Компактный</span><span>Увеличенный</span></div>
        </section>

        <section className="appearance-card appearance-card-wide">
          <SectionHeading
            icon={ImagePlus}
            title="Фоновое изображение"
            description="Добавь собственные обои в рабочее пространство"
          />

          <div className={`wallpaper-preview ${backgroundImage ? "has-image" : ""}`}>
            {backgroundImage && <img src={backgroundImage} alt="Текущий фон NEXUS" />}
            <div className="wallpaper-preview-overlay">
              {backgroundImage ? (
                <span><Check size={15} /> Фоновое изображение установлено</span>
              ) : (
                <span><ImagePlus size={19} /> Фоновое изображение не выбрано</span>
              )}
            </div>
          </div>

          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            hidden
            onChange={chooseImage}
          />

          <div className="wallpaper-actions">
            <button className="appearance-primary-button" onClick={() => fileRef.current?.click()}>
              <Upload size={15} /> Загрузить изображение
            </button>
            {backgroundImage && (
              <button
                className="appearance-secondary-button"
                onClick={() => appearance.set({ backgroundImage: "" })}
              >
                <X size={14} /> Удалить фон
              </button>
            )}
          </div>

          <WallpaperBrowser onApply={(url) => {
            appearance.set({ backgroundImage: url });
            setNotice("Онлайн-обои установлены.");
          }} />
          <div className="appearance-slider-block">
            <div className="slider-heading">
              <span><Eye size={14} /> Затемнение</span>
              <strong>{backgroundDim}%</strong>
            </div>
            <input
              className="appearance-range"
              type="range"
              min="0"
              max="90"
              step="5"
              value={backgroundDim}
              onChange={(event) => appearance.set({ backgroundDim: Number(event.target.value) })}
            />
          </div>

          <div className="appearance-slider-block">
            <div className="slider-heading">
              <span><Droplets size={14} /> Размытие</span>
              <strong>{backgroundBlur}px</strong>
            </div>
            <input
              className="appearance-range"
              type="range"
              min="0"
              max="30"
              step="1"
              value={backgroundBlur}
              onChange={(event) => appearance.set({ backgroundBlur: Number(event.target.value) })}
            />
          </div>
        </section>

        <section className="appearance-card">
          <SectionHeading
            icon={Layers}
            title="Liquid Glass"
            description="Стеклянные поверхности и размытие"
          />

          <button
            className={`liquid-glass-option ${liquidGlass ? "enabled" : ""}`}
            onClick={() => appearance.set({ liquidGlass: !liquidGlass })}
          >
            <span className="liquid-glass-icon"><Sparkles size={19} /></span>
            <span className="liquid-glass-copy">
              <strong>Эффект стекла</strong>
              <small>{liquidGlass ? "Включён" : "Выключен"}</small>
            </span>
            <span className={`appearance-switch ${liquidGlass ? "on" : ""}`} />
          </button>

          <div className="liquid-glass-description">
            <Settings2 size={14} />
            Меняет материалы панелей и интенсивность стеклянного размытия.
          </div>
        </section>
      </div>

      <div className="appearance-footer">
        <span><Check size={13} /> Параметры сохраняются автоматически</span>
        <span>NEXUS APPEARANCE</span>
      </div>
    </div>
  );
}



