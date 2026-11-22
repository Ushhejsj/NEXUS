import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  Search, Image, Download, ChevronLeft, ChevronRight, LoaderCircle
} from "lucide-react";
import "./WallpaperBrowser.css";

type Category = "anime" | "general" | "people";

type Wallpaper = {
  id: string;
  path: string;
  resolution: string;
  thumbs: { large: string };
};

type ApiResult = {
  data: Wallpaper[];
  meta: { current_page: number; last_page: number };
};

const categories: { id: Category; label: string }[] = [
  { id: "anime", label: "Аниме" },
  { id: "general", label: "Общие" },
  { id: "people", label: "Люди" }
];

const colors = [
  "660000", "990000", "cc0000", "cc3333", "ea4c88",
  "993399", "663399", "333399", "0066cc", "0099cc",
  "66cccc", "77cc33", "669900", "336600", "666600",
  "999900", "cccc33", "ffff00", "ffcc33", "ff9900",
  "ff6600", "cc6633", "996633", "663300", "000000",
  "999999", "cccccc", "ffffff", "424153"
];

export default function WallpaperBrowser({
  onApply
}: {
  onApply: (url: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("anime");
  const [color, setColor] = useState<string | null>(null);
  const [items, setItems] = useState<Wallpaper[]>([]);
  const [selected, setSelected] = useState<Wallpaper | null>(null);
  const [page, setPage] = useState(1);
  const [lastPage, setLastPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async (
    nextPage = 1,
    search = query,
    nextCategory = category,
    nextColor = color
  ) => {
    setLoading(true);
    setError("");

    try {
      const result = await invoke<ApiResult>("wallhaven_search", {
        page: nextPage,
        search: search.trim(),
        category: nextCategory,
        color: nextColor
      });

      setItems(result.data ?? []);
      setPage(result.meta?.current_page ?? nextPage);
      setLastPage(result.meta?.last_page ?? 1);
      setSelected(null);
    } catch (err) {
      setError(`Не удалось загрузить обои: ${String(err)}`);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(1, query, category, color);
  }, [category, color]);

  return (
    <section className="wallpaper-browser">
      <div className="wallpaper-browser-heading">
        <div>
          <strong>Онлайн-обои</strong>
          <span>
            Популярные изображения Wallhaven · безопасный контент · от 1920×1080
          </span>
        </div>
        <span className="wallpaper-source-label">WALLHAVEN</span>
      </div>

      <form
        className="wallpaper-search"
        onSubmit={(e) => {
          e.preventDefault();
          void load(1);
        }}
      >
        <Search size={17} />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Например: space, nature, cyberpunk..."
        />
        <button type="submit" disabled={loading}>Найти</button>
      </form>

      <div className="wallpaper-filter-label">Категория</div>
      <div className="wallpaper-category-options">
        {categories.map((item) => (
          <button
            key={item.id}
            type="button"
            aria-pressed={category === item.id}
            className={category === item.id ? "active" : ""}
            onClick={() => setCategory(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="wallpaper-filter-label">Основной цвет</div>
      <div className="wallpaper-color-options">
        <button
          type="button"
          className={`wallpaper-color-any ${color === null ? "active" : ""}`}
          onClick={() => setColor(null)}
        >
          Любой
        </button>
        {colors.map((value) => (
          <button
            key={value}
            type="button"
            title={`#${value}`}
            aria-label={`Цвет #${value}`}
            aria-pressed={color === value}
            className={`wallpaper-color ${color === value ? "active" : ""}`}
            style={{ backgroundColor: `#${value}` }}
            onClick={() => setColor(color === value ? null : value)}
          />
        ))}
      </div>

      {error && <div className="wallpaper-error">{error}</div>}

      {loading ? (
        <div className="wallpaper-loading">
          <LoaderCircle size={22} />
          Загружаем изображения...
        </div>
      ) : (
        <>
          <div className="wallpaper-gallery">
            {items.map((item) => (
              <button
                type="button"
                key={item.id}
                className={`wallpaper-tile ${selected?.id === item.id ? "selected" : ""}`}
                onClick={() => setSelected(item)}
                title={`${item.id} · ${item.resolution}`}
              >
                <img
                  src={item.thumbs.large}
                  alt="Обои"
                  loading="lazy"
                />
                <span>{item.resolution}</span>
              </button>
            ))}
          </div>

          {!items.length && !error && (
            <div className="wallpaper-empty">
              <Image size={24} />
              <span>Изображения не найдены</span>
            </div>
          )}

          <div className="wallpaper-browser-footer">
            <button
              type="button"
              disabled={page <= 1 || loading}
              onClick={() => void load(page - 1)}
            >
              <ChevronLeft size={16} /> Назад
            </button>
            <span>{page} / {lastPage}</span>
            <button
              type="button"
              disabled={page >= lastPage || loading}
              onClick={() => void load(page + 1)}
            >
              Далее <ChevronRight size={16} />
            </button>
          </div>
        </>
      )}

      {selected && (
        <div className="wallpaper-selected">
          <img
            src={selected.thumbs.large}
            alt="Предпросмотр выбранных обоев"
          />
          <div className="wallpaper-selected-info">
            <strong>{selected.id}</strong>
            <span>{selected.resolution}</span>
          </div>
          <button type="button" onClick={() => onApply(selected.path)}>
            <Download size={15} /> Установить фоном
          </button>
        </div>
      )}
    </section>
  );
}