import type { Lang } from "../i18n";
import { readSse } from "./sse";
import type {
  AISettings,
  AIStatus,
  AIUsage,
  Checkpoint,
  CreateGameRequest,
  DonePayload,
  GameSummary,
  GameView,
  JournalEntry,
  Memories,
  OutcomePayload,
  TurnIntent,
  TurnView,
} from "./types";

/** Error with a stable code that maps to an i18n key (errors.<code>). */
export class ApiError extends Error {
  constructor(
    public code: string,
    public status: number,
    public detail?: unknown,
  ) {
    super(code);
  }
}

interface Runtime {
  baseUrl: string;
  token: string | null;
}

// The desktop shell injects its sidecar address and per-launch token here.
declare global {
  interface Window {
    __CANECA_RUNTIME__?: Partial<Runtime>;
  }
}

function runtime(): Runtime {
  const injected = typeof window !== "undefined" ? window.__CANECA_RUNTIME__ : undefined;
  return {
    baseUrl: injected?.baseUrl ?? import.meta.env.VITE_API_BASE ?? "",
    token: injected?.token ?? null,
  };
}

function headers(extra?: HeadersInit): Headers {
  const h = new Headers(extra);
  const { token } = runtime();
  if (token) h.set("Authorization", `Bearer ${token}`);
  return h;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${runtime().baseUrl}${path}`, {
      ...init,
      headers: headers({ "Content-Type": "application/json", ...(init.headers ?? {}) }),
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError("network", 0);
  }
  if (!resp.ok) throw await toError(resp);
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

async function toError(resp: Response): Promise<ApiError> {
  try {
    const body = (await resp.json()) as { error?: { code?: string; detail?: unknown } };
    return new ApiError(body.error?.code ?? "generic", resp.status, body.error?.detail);
  } catch {
    return new ApiError("generic", resp.status);
  }
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });
const q = (lang?: Lang) => (lang ? `?lang=${encodeURIComponent(lang)}` : "");

export const api = {
  health: () => request<{ status: string; version: string }>("/api/health"),
  listGames: () => request<GameSummary[]>("/api/games"),
  createGame: (req: CreateGameRequest) => request<GameView>("/api/games", { method: "POST", ...json(req) }),
  getGame: (id: string, lang?: Lang) => request<GameView>(`/api/games/${id}${q(lang)}`),
  updateGame: (id: string, patch: { name?: string; settings?: GameView["settings"] }) =>
    request<GameView>(`/api/games/${id}`, { method: "PATCH", ...json(patch) }),
  deleteGame: (id: string) => request<void>(`/api/games/${id}`, { method: "DELETE" }),
  history: (id: string, before?: number, lang?: Lang) => {
    const params = new URLSearchParams({ limit: "40" });
    if (before !== undefined) params.set("before", String(before));
    if (lang) params.set("lang", lang);
    return request<{ turns: TurnView[]; has_more: boolean }>(`/api/games/${id}/turns?${params}`);
  },
  journal: (id: string, lang?: Lang) => request<JournalEntry[]>(`/api/games/${id}/journal${q(lang)}`),
  memories: (id: string, lang?: Lang) => request<Memories>(`/api/games/${id}/memories${q(lang)}`),
  checkpoints: (id: string) => request<Checkpoint[]>(`/api/games/${id}/checkpoints`),
  createCheckpoint: (id: string, label: string) =>
    request<Checkpoint>(`/api/games/${id}/checkpoints`, { method: "POST", ...json({ label }) }),
  restoreCheckpoint: (id: string, cp: number) =>
    request<GameView>(`/api/games/${id}/checkpoints/${cp}/restore`, { method: "POST" }),
  deleteCheckpoint: (id: string, cp: number) =>
    request<void>(`/api/games/${id}/checkpoints/${cp}`, { method: "DELETE" }),
  exportGame: (id: string) => request<unknown>(`/api/games/${id}/export`),
  importGame: (data: string) =>
    request<GameView>("/api/games/import", { method: "POST", body: data }),
  cancel: (id: string) => request<{ cancelled: boolean }>(`/api/games/${id}/cancel`, { method: "POST" }),
  aiSettings: () => request<AISettings>("/api/ai/settings"),
  saveAiSettings: (s: AISettings) => {
    const { keys: _keys, ...body } = s;
    return request<AISettings>("/api/ai/settings", { method: "PUT", ...json(body) });
  },
  aiStatus: (provider: string) => request<AIStatus>(`/api/ai/status?provider=${provider}`),
  aiTest: (provider: string, model: string) =>
    request<{ ok: boolean; latency_ms?: number; sample?: string; code?: string; detail?: string }>(
      "/api/ai/test",
      { method: "POST", ...json({ provider, model }) },
    ),
  setKey: (provider: string, key: string) =>
    request<void>(`/api/ai/keys/${provider}`, { method: "PUT", ...json({ key }) }),
  deleteKey: (provider: string) => request<void>(`/api/ai/keys/${provider}`, { method: "DELETE" }),
  aiUsage: () => request<AIUsage[]>("/api/ai/usage"),
  backup: () => request<{ file: string }>("/api/system/backup", { method: "POST" }),
};

export interface TurnHandlers {
  onOutcome: (o: OutcomePayload) => void;
  onDelta: (text: string) => void;
  onDone: (d: DonePayload) => void;
  onWarning: (code: string) => void;
}

/** Plays one turn, streaming the narration. Resolves when the stream ends. */
export async function playTurn(
  gameId: string,
  body: { text: string; intent?: TurnIntent; expected_turn?: number },
  handlers: TurnHandlers,
  signal: AbortSignal,
): Promise<void> {
  let resp: Response;
  try {
    resp = await fetch(`${runtime().baseUrl}/api/games/${gameId}/turns`, {
      method: "POST",
      headers: headers({ "Content-Type": "application/json", Accept: "text/event-stream" }),
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError("network", 0);
  }
  if (!resp.ok || !resp.body) throw await toError(resp);
  for await (const ev of readSse(resp.body)) {
    const data = JSON.parse(ev.data) as Record<string, unknown>;
    switch (ev.event) {
      case "outcome":
        handlers.onOutcome(data as unknown as OutcomePayload);
        break;
      case "delta":
        handlers.onDelta(String(data.text ?? ""));
        break;
      case "done":
        handlers.onDone(data as unknown as DonePayload);
        break;
      case "warning":
        handlers.onWarning(String(data.code ?? "ai_unavailable"));
        break;
      case "error":
        throw new ApiError(String(data.code ?? "internal"), 500, data.detail);
    }
  }
}
