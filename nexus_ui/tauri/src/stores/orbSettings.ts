import { create } from "zustand";
import { persist } from "zustand/middleware";

export type OrbStyle = "ENERGY" | "PARTICLES" | "HOLOGRAM" | "FLUID" | "VERITY";
export type OrbState = "SLEEP" | "WAKE_UP" | "LISTENING" | "THINKING" | "EXECUTING";

type OrbSettingsValues = {
  style: OrbStyle;
  state: OrbState;
  primary: string;
  secondary: string;
  glow: number;
  speed: number;
  particleCount: number;
  scale: number;
};

type OrbSettingsStore = OrbSettingsValues & {
  set: (values: Partial<OrbSettingsValues>) => void;
};

export const useOrbSettings = create<OrbSettingsStore>()(
  persist(
    (set) => ({
      style: "ENERGY",
      state: "SLEEP",
      primary: "#B995E8",
      secondary: "#F1C2A9",
      glow: 1,
      speed: 1,
      particleCount: 180,
      scale: 1,
      set: (values) => set(values),
    }),
    { name: "nexus-orb-settings-v1" }
  )
);
