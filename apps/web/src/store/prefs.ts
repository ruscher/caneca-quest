import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";
import { detectLanguage, type Lang } from "../i18n";

export type ThemePref = "auto" | "light" | "dark";
export type ReadingFont = "literata" | "atkinson" | "sans";
export type MotionPref = "auto" | "full" | "reduced";
export type TextSpeed = "instant" | "fast" | "normal" | "slow";

export interface Prefs {
  language: Lang;
  theme: ThemePref;
  fontScale: number;
  readingFont: ReadingFont;
  motion: MotionPref;
  textSpeed: TextSpeed;
  showChecks: boolean;
  weather: boolean;
  audio: boolean;
  volume: number;
  tts: boolean;
  voiceURI: string;
  lastGameId: string | null;
}

interface PrefsStore extends Prefs {
  set: (patch: Partial<Prefs>) => void;
}

/** localStorage can be missing or throw (private mode, blocked storage): never crash. */
const safeStorage: StateStorage = {
  getItem: (name) => {
    try {
      return localStorage.getItem(name);
    } catch {
      return null;
    }
  },
  setItem: (name, value) => {
    try {
      localStorage.setItem(name, value);
    } catch {
      /* preferences simply won't persist */
    }
  },
  removeItem: (name) => {
    try {
      localStorage.removeItem(name);
    } catch {
      /* ignore */
    }
  },
};

export const DEFAULT_PREFS: Prefs = {
  language: detectLanguage(),
  theme: "auto",
  fontScale: 1,
  readingFont: "literata",
  motion: "auto",
  textSpeed: "normal",
  showChecks: true,
  weather: true,
  audio: false,
  volume: 0.5,
  tts: false,
  voiceURI: "",
  lastGameId: null,
};

export const usePrefs = create<PrefsStore>()(
  persist(
    (set) => ({
      ...DEFAULT_PREFS,
      set: (patch) => set(patch),
    }),
    {
      name: "caneca-prefs",
      version: 1,
      storage: createJSONStorage(() => safeStorage),
      partialize: ({ set: _set, ...rest }) => rest,
    },
  ),
);

export const TEXT_SPEED_CPS: Record<TextSpeed, number> = {
  instant: Infinity,
  fast: 140,
  normal: 70,
  slow: 35,
};

export function resolvedTheme(pref: ThemePref): "light" | "dark" {
  if (pref !== "auto") return pref;
  return typeof matchMedia !== "undefined" && matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function prefersReducedMotion(pref: MotionPref): boolean {
  if (pref === "reduced") return true;
  if (pref === "full") return false;
  return typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;
}
