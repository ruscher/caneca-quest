import { create } from "zustand";
import { ApiError, api, playTurn } from "../api/client";
import type {
  CheckView,
  CreateGameRequest,
  EventView,
  GameView,
  NarrationSource,
  Suggestion,
  TurnView,
} from "../api/types";
import { usePrefs } from "./prefs";

export type Screen = "welcome" | "create" | "game" | "saves" | "help" | "credits";
export type Phase = "idle" | "resolving" | "narrating";

export interface FeedEntry {
  id: string;
  turn: number;
  kind: "intro" | "player" | "narration" | "notice";
  text: string;
  source?: NarrationSource;
  events?: EventView[];
  check?: CheckView | null;
  streaming?: boolean;
  /** Typewriter reveal for freshly produced, non-streamed text. */
  animate?: boolean;
  fallback?: string;
}

export interface Toast {
  id: number;
  kind: "info" | "success" | "warning" | "error" | "achievement" | "quest";
  text: string;
}

interface GameStore {
  screen: Screen;
  settingsOpen: boolean;
  game: GameView | null;
  feed: FeedEntry[];
  hasMore: boolean;
  loadingHistory: boolean;
  phase: Phase;
  toasts: Toast[];
  commandHistory: string[];
  lastError: string | null;
  narration: { text: string; id: number } | null;

  go: (screen: Screen) => void;
  openSettings: (open: boolean) => void;
  openGame: (id: string) => Promise<void>;
  startGame: (req: CreateGameRequest) => Promise<void>;
  setGame: (view: GameView) => void;
  reloadFeed: () => Promise<void>;
  act: (text: string, intent?: Suggestion | null) => Promise<void>;
  cancel: () => void;
  loadOlder: () => Promise<void>;
  toast: (kind: Toast["kind"], text: string) => void;
  dismissToast: (id: number) => void;
  closeGame: () => void;
}

let controller: AbortController | null = null;
let toastSeq = 0;
let entrySeq = 0;
const newId = (prefix: string) => `${prefix}-${Date.now().toString(36)}-${(entrySeq++).toString(36)}`;

function turnsToFeed(turns: TurnView[]): FeedEntry[] {
  const out: FeedEntry[] = [];
  for (const t of turns) {
    if (t.kind === "action" && t.player_input) {
      out.push({ id: `p-${t.number}`, turn: t.number, kind: "player", text: t.player_input });
    }
    out.push({
      id: `n-${t.number}`,
      turn: t.number,
      kind: t.kind === "intro" ? "intro" : "narration",
      text: t.narration,
      source: t.source,
      events: t.events,
    });
  }
  return out;
}

/** Error codes resolved to messages by the UI layer (errors.<code>). */
export function errorCode(err: unknown): string {
  if (err instanceof ApiError) return err.code;
  return "generic";
}

export const useGame = create<GameStore>((set, get) => ({
  screen: "welcome",
  settingsOpen: false,
  game: null,
  feed: [],
  hasMore: false,
  loadingHistory: false,
  phase: "idle",
  toasts: [],
  commandHistory: [],
  lastError: null,
  narration: null,

  go: (screen) => set({ screen }),
  openSettings: (open) => set({ settingsOpen: open }),

  setGame: (view) => set({ game: view }),

  openGame: async (id) => {
    const lang = usePrefs.getState().language;
    const view = await api.getGame(id, lang);
    if (view.language !== lang) {
      // Keep the story language aligned with the interface language.
      const updated = await api.updateGame(id, { settings: { ...view.settings, language: lang } });
      set({ game: updated });
    } else {
      set({ game: view });
    }
    usePrefs.getState().set({ lastGameId: id });
    await get().reloadFeed();
    set({ screen: "game" });
  },

  startGame: async (req) => {
    const view = await api.createGame(req);
    usePrefs.getState().set({ lastGameId: view.id });
    set({ game: view, feed: [], commandHistory: [] });
    await get().reloadFeed();
    const feed = get().feed.map((e) => (e.kind === "intro" ? { ...e, animate: true } : e));
    set({ feed, screen: "game" });
  },

  reloadFeed: async () => {
    const game = get().game;
    if (!game) return;
    const hist = await api.history(game.id, undefined, usePrefs.getState().language);
    set({ feed: turnsToFeed(hist.turns), hasMore: hist.has_more });
  },

  loadOlder: async () => {
    const { game, feed, loadingHistory, hasMore } = get();
    if (!game || loadingHistory || !hasMore) return;
    const first = feed.find((e) => e.kind !== "player");
    if (!first) return;
    set({ loadingHistory: true });
    try {
      const hist = await api.history(game.id, first.turn, usePrefs.getState().language);
      set({ feed: [...turnsToFeed(hist.turns), ...get().feed], hasMore: hist.has_more });
    } finally {
      set({ loadingHistory: false });
    }
  },

  act: async (text, suggestion) => {
    const { game, phase } = get();
    const trimmed = text.trim();
    if (!game || phase !== "idle" || !trimmed) return;
    const playerEntry: FeedEntry = { id: newId("p"), turn: game.turn + 1, kind: "player", text: trimmed };
    const narrationId = newId("n");
    controller = new AbortController();
    set({
      phase: "resolving",
      feed: [...get().feed, playerEntry],
      commandHistory: [trimmed, ...get().commandHistory.filter((c) => c !== trimmed)].slice(0, 50),
      lastError: null,
    });

    const updateEntry = (patch: Partial<FeedEntry> | ((e: FeedEntry) => Partial<FeedEntry>)) =>
      set({
        feed: get().feed.map((e) =>
          e.id === narrationId ? { ...e, ...(typeof patch === "function" ? patch(e) : patch) } : e,
        ),
      });

    try {
      await playTurn(
        game.id,
        {
          text: trimmed,
          expected_turn: game.turn,
          intent: suggestion
            ? {
                verb: suggestion.verb,
                target: suggestion.target,
                item: suggestion.item,
                interaction: suggestion.interaction,
              }
            : undefined,
        },
        {
          onOutcome: (o) => {
            set({
              game: o.view,
              phase: "narrating",
              feed: [
                ...get().feed,
                {
                  id: narrationId,
                  turn: o.turn ?? o.view.turn,
                  kind: "narration",
                  text: "",
                  fallback: o.fallback,
                  events: o.events,
                  check: o.check,
                  streaming: true,
                },
              ],
            });
            announceEvents(o.events, get().toast);
          },
          onDelta: (delta) => updateEntry((e) => ({ text: e.text + delta })),
          onDone: (d) => {
            updateEntry((e) => ({
              text: d.narration,
              source: d.source,
              streaming: false,
              animate: d.source === "engine" && !e.text,
            }));
            set({ narration: { text: d.narration, id: Date.now() } });
          },
          onWarning: (code) => get().toast("warning", code),
        },
        controller.signal,
      );
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        void api.cancel(game.id).catch(() => undefined);
        updateEntry((e) => ({
          text: e.text.trim() || e.fallback || "",
          source: "cancelled",
          streaming: false,
        }));
      } else {
        const code = errorCode(err);
        set({ lastError: code });
        get().toast("error", code);
        if (code === "conflict") {
          const fresh = await api.getGame(game.id).catch(() => null);
          if (fresh) set({ game: fresh });
          await get().reloadFeed().catch(() => undefined);
        } else if (!get().feed.some((e) => e.id === narrationId)) {
          // The turn never reached the engine: drop the optimistic player entry.
          set({ feed: get().feed.filter((e) => e.id !== playerEntry.id) });
        } else {
          updateEntry((e) => ({ text: e.text || e.fallback || "", streaming: false, source: "fallback" }));
        }
      }
    } finally {
      controller = null;
      set({ phase: "idle" });
    }
  },

  cancel: () => {
    controller?.abort();
  },

  toast: (kind, text) => {
    const id = ++toastSeq;
    set({ toasts: [...get().toasts.slice(-3), { id, kind, text }] });
    setTimeout(() => get().dismissToast(id), kind === "error" ? 7000 : 4500);
  },

  dismissToast: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),

  closeGame: () => {
    controller?.abort();
    set({ game: null, feed: [], screen: "welcome", phase: "idle" });
  },
}));

const TOAST_EVENTS: Record<string, Toast["kind"]> = {
  quest_started: "quest",
  quest_completed: "success",
  objective: "quest",
  achievement: "achievement",
  level_up: "success",
  ability_learned: "success",
  chapter: "quest",
};

function announceEvents(events: EventView[], toast: GameStore["toast"]) {
  for (const ev of events) {
    const kind = TOAST_EVENTS[ev.kind];
    if (kind && ev.label) toast(kind, `raw:${ev.label}`);
  }
}
