import {
  Check, Crown, Sparkles, Zap, BrainCircuit, Mic2,
  Workflow, Monitor, Palette, Clock3
} from "lucide-react";
import "./SubscriptionPage.css";
import { invoke } from "@tauri-apps/api/core";
import { useSubscriptionStore } from "../stores/subscription";

const groups = [
  {
    title: "Основные возможности",
    icon: Monitor,
    features: [
      ["Запуск приложений и управление компьютером", true, true],
      ["Голосовое управление и распознавание команд", true, true],
      ["Память NEXUS", true, true],
      ["Макросы без ограничений", true, true],
    ],
  },
  {
    title: "Искусственный интеллект",
    icon: BrainCircuit,
    features: [
      ["Одна нейросеть на выбор", true, true],
      ["Дополнительные AI-провайдеры", false, true],
      ["До 4 нейросетей одновременно", false, true],
      ["Сравнение ответов нейросетей", false, true],
    ],
  },
  {
    title: "Голос и автоматизация",
    icon: Mic2,
    features: [
      ["Один базовый голос озвучивания", true, true],
      ["Выбор и добавление собственных голосов", false, true],
      ["Интеллектуальная оптимизация запуска", false, true],
      ["Автоматическое составление сценариев", false, true],
      ["Создание сценариев через Telegram", false, true],
      ["Расширенное удалённое управление", false, true],
      ["Фоновая работа и запланированные задачи", false, true],
    ],
  },
  {
    title: "Персонализация",
    icon: Palette,
    features: [
      ["Темы, цвета, шрифты и фоны", true, true],
      ["Liquid Glass", true, true],
      ["Настройка внешнего вида орбов", true, true],
    ],
  },
];

function FeatureMark({ enabled }: { enabled: boolean }) {
  return enabled
    ? <Check className="plan-feature-check" size={16} />
    : <span className="plan-feature-dash">—</span>;
}

export default function SubscriptionPage() {
  const plan = useSubscriptionStore((state) => state.plan);
  const devTitan = useSubscriptionStore((state) => state.devTitan);
  const hydrate = useSubscriptionStore((state) => state.hydrate);

  const toggleDevTitan = async () => {
    try {
      await invoke("set_dev_titan", { enabled: !devTitan });
      await hydrate();
    } catch (error) {
      console.error("Не удалось переключить тестовый TITAN:", error);
    }
  };
  return (
    <div className="subscription-page">
      <header className="subscription-heading">
        <div className="subscription-overline"><Sparkles size={13} /> NEXUS MEMBERSHIP</div>
        <h1>Выбери свой уровень <span>NEXUS</span></h1>
        <p>Базовые возможности остаются бесплатными. TITAN открывает расширенный интеллект и автоматизацию.</p>
      </header>

      <div className="subscription-plans">
        <article className="subscription-plan free-plan">
          <div className="plan-topline">
            <div className="plan-icon"><Monitor size={20} /></div>
            <span className="plan-label">БАЗОВЫЙ ДОСТУП</span>
          </div>
          <h2>NEXUS FREE</h2>
          <div className="plan-price">0 ₽ <small>/ навсегда</small></div>
          <p className="plan-description">Всё необходимое для повседневного управления компьютером.</p>
          <div className="plan-status"><Check size={14} /> {plan === "free" ? "Текущий тариф" : "Бесплатный тариф"}</div>
        </article>

        <article className="subscription-plan titan-plan">
          <div className="titan-glow" />
          <div className="plan-topline">
            <div className="plan-icon"><Crown size={20} /></div>
            <span className="plan-label">РАСШИРЕННЫЕ ВОЗМОЖНОСТИ</span>
          </div>
          <h2>NEXUS <span>TITAN</span></h2>
          <div className="plan-price">500 ₽ <small>/ месяц</small></div>
          <div className="plan-year-price">4 500 ₽ / год — экономия 1 500 ₽</div>
          <p className="plan-description">Больше нейросетей, собственные голоса и интеллектуальная автоматизация.</p>
          <div className="plan-status titan-status"><Zap size={14} /> {plan === "titan" ? "Текущий тариф" : "Подписка готовится к запуску"}</div>
          {import.meta.env.DEV && (
            <button
              type="button"
              className="dev-titan-button"
              onClick={toggleDevTitan}
            >
              {devTitan ? "Отключить тестовый TITAN" : "Активировать TITAN для тестирования"}
            </button>
          )}
        </article>
      </div>

      <section className="subscription-comparison">
        <div className="comparison-heading">
          <div>
            <span className="subscription-overline">ВОЗМОЖНОСТИ</span>
            <h2>Сравнение тарифов</h2>
          </div>
          <div className="comparison-columns">
            <span>FREE</span>
            <span className="titan-column">TITAN</span>
          </div>
        </div>

        {groups.map((group) => {
          const Icon = group.icon;
          return (
            <div className="comparison-group" key={group.title}>
              <div className="comparison-group-title"><Icon size={16} /> {group.title}</div>
              {group.features.map(([name, free, titan]) => (
                <div className="comparison-row" key={name as string}>
                  <span className="comparison-feature">{name}</span>
                  <FeatureMark enabled={free as boolean} />
                  <FeatureMark enabled={titan as boolean} />
                </div>
              ))}
            </div>
          );
        })}
      </section>

      <div className="subscription-note">
        <Clock3 size={17} />
        <p>Оплата и автоматическая активация TITAN появятся после подключения платёжной системы. До этого базовые функции NEXUS остаются бесплатными.</p>
      </div>

      <div className="subscription-footer">
        <ShieldText />
        <span>Никаких искусственных ограничений базовых функций.</span>
      </div>
    </div>
  );
}

function ShieldText() {
  return <Workflow size={15} />;
}






