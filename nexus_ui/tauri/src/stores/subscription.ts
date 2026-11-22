import { create } from "zustand";
import { invoke } from "@tauri-apps/api/core";

export type NexusPlan = "free" | "titan";

export type PremiumFeature =
  | "extraAiProviders"
  | "multiAi"
  | "customVoices"
  | "intelligentLaunch"
  | "autonomousAutomation"
  | "telegramAutomation"
  | "advancedRemoteControl"
  | "backgroundTasks";

type SubscriptionInfo = {
  plan: NexusPlan;
  status: string;
  devTitan: boolean;
};

type SubscriptionState = {
  plan: NexusPlan;
  status: string;
  devTitan: boolean;
  loading: boolean;
  hydrate: () => Promise<void>;
};

export const useSubscriptionStore = create<SubscriptionState>((set) => ({
  plan: "free",
  status: "active",
  devTitan: false,
  loading: true,
  hydrate: async () => {
    try {
      const subscription = await invoke<SubscriptionInfo>("get_subscription");
      set({
        plan: subscription.plan,
        status: subscription.status,
        devTitan: subscription.devTitan,
        loading: false,
      });
    } catch (error) {
      console.error("Не удалось получить статус подписки:", error);
      set({ plan: "free", status: "active", devTitan: false, loading: false });
    }
  },
}));

const premiumFeatures: PremiumFeature[] = [
  "extraAiProviders",
  "multiAi",
  "customVoices",
  "intelligentLaunch",
  "autonomousAutomation",
  "telegramAutomation",
  "advancedRemoteControl",
  "backgroundTasks",
];

export function canUseFeature(feature: PremiumFeature, plan: NexusPlan): boolean {
  return !premiumFeatures.includes(feature) || plan === "titan";
}


