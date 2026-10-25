// Mirrors the backend read models (backend/caneca/api/views.py).
import type { Lang } from "../i18n";

export type Tone = "balanced" | "fantasy" | "mystery" | "humor" | "drama" | "relaxing" | "survival";
export type Difficulty = "story" | "adventure" | "survival";
export type NarrativeLength = "short" | "normal" | "detailed" | "cinematic";
export type Material = "porcelain" | "stoneware" | "enamel" | "glass";
export type Drink = "black_coffee" | "latte" | "cappuccino" | "hot_chocolate" | "tea";
export type Style = "classic" | "striped" | "dotted" | "floral" | "minimal" | "rustic";
export type Personality = "optimistic" | "sarcastic" | "shy" | "philosophical" | "fearless";
export type Trait = "brave" | "creative" | "sturdy" | "thermal" | "curious" | "charming";

export interface Mug {
  name: string;
  color: string;
  style: Style;
  material: Material;
  drink: Drink;
  personality: Personality;
  traits: Trait[];
}

export interface AdventureSettings {
  tone: Tone;
  difficulty: Difficulty;
  narrative_length: NarrativeLength;
  language: Lang;
}

export interface Stats {
  temperature: number;
  coffee: number;
  integrity: number;
  energy: number;
  courage: number;
  creativity: number;
  xp: number;
  level: number;
  xp_level_start: number;
  xp_next: number;
}

export interface Suggestion {
  label: string;
  verb: string;
  target: string | null;
  item: string | null;
  kind: string;
  interaction: string | null;
}

export interface NamedRef {
  id: string;
  name: string;
}

export interface LocationView {
  id: string;
  name: string;
  short: string;
  description: string;
  region: string;
  dark: boolean;
  heat: boolean;
  ambient_temp: number;
  features: NamedRef[];
  items: (NamedRef & { icon: string })[];
  npcs: (NamedRef & { kind: string; icon: string; remote: boolean; mood: string })[];
  exits: { to: string; label: string; kind: string; allowed: boolean; visited: boolean }[];
}

export interface Ability {
  id: string;
  name: string;
  description: string;
  kind: "active" | "passive";
  cooldown: number;
  cost_energy: number;
  cost_coffee: number;
}

export interface InventoryItem {
  id: string;
  name: string;
  description: string;
  icon: string;
  weight: number;
}

export interface Quest {
  id: string;
  kind: "main" | "side" | "secret" | "emergent" | "npc" | "exploration";
  name: string;
  description: string;
  status: "active" | "completed" | "failed";
  outcome: string | null;
  objectives: { id: string; text: string; done: boolean; optional: boolean }[];
  started_turn: number | null;
}

export interface Relationship {
  id: string;
  name: string;
  kind: string;
  icon: string;
  value: number;
  label: string;
  mood: string;
  location: string;
  companion: boolean;
  memories: number;
}

export interface MapView {
  regions: { id: string; name: string; chapter: number; palette: string; known: boolean }[];
  nodes: { id: string; name: string; region: string; x: number; y: number; visited: boolean; current: boolean }[];
  edges: [string, string][];
}

export interface GameView {
  id: string;
  name: string;
  status: "active" | "ended" | "defeated";
  version: number;
  created_at: string;
  updated_at: string;
  turn: number;
  language: Lang;
  settings: AdventureSettings;
  mug: Mug;
  chapter: { number: number; title: string };
  region: { id: string; name: string; palette: string };
  clock: string;
  stats: Stats;
  statuses: { id: string; label: string }[];
  abilities: Ability[];
  location: LocationView;
  inventory: InventoryItem[];
  capacity: { used: number; max: number };
  quests: Quest[];
  relationships: Relationship[];
  map: MapView;
  achievements: { id: string; name: string; description: string; unlocked: boolean }[];
  codex: { id: string; kind: "npc" | "item" | "location" | "feature"; name: string; description: string }[];
  suggestions: Suggestion[];
  ending: { id: string; name: string; text: string; kind: "victory" | "bittersweet" | "defeat" } | null;
  defeated: boolean;
}

export interface GameSummary {
  id: string;
  name: string;
  status: GameView["status"];
  version: number;
  created_at: string;
  updated_at: string;
  turn: number;
  chapter: number;
  location: string;
  mug: Mug;
  level: number;
  language: Lang;
}

export interface CheckView {
  stat: string;
  dc: number;
  roll: number;
  modifier: number;
  total: number;
  outcome: "critical" | "success" | "partial" | "failure";
}

export interface EventView {
  kind: string;
  label?: string | null;
  stat?: string;
  delta?: number;
  value?: number;
  amount?: number;
  [key: string]: unknown;
}

export type NarrationSource = "engine" | "ai" | "fallback" | "cancelled";

export interface TurnView {
  number: number;
  kind: "intro" | "action";
  player_input: string;
  narration: string;
  source: NarrationSource;
  events: EventView[];
  created_at: string;
}

export interface OutcomePayload {
  turn: number | null;
  intent: { verb: string; target: string | null; item: string | null; source: string };
  check: CheckView | null;
  success: boolean | null;
  fallback: string;
  events: EventView[];
  view: GameView;
}

export interface DonePayload {
  narration: string;
  source: NarrationSource;
  usage?: { tokens_in: number; tokens_out: number };
}

export interface TurnIntent {
  verb: string;
  target: string | null;
  item: string | null;
  interaction: string | null;
}

export interface JournalEntry {
  id: number;
  turn: number;
  kind: string;
  title: string;
  body: string;
  location: string;
  participants: string[];
  decision: string;
}

export interface Memories {
  summary: string;
  facts: { id: string; text: string; turn: number; importance: number; location: string; known_by: string[] }[];
}

export interface Checkpoint {
  id: number;
  label: string;
  turn: number;
  auto: boolean;
  created_at: string;
}

export type ProviderId = "offline" | "ollama" | "openai" | "anthropic";

export interface AISettings {
  provider: ProviderId;
  models: Partial<Record<Exclude<ProviderId, "offline">, string>>;
  ollama_url: string;
  openai_base_url: string;
  temperature: number;
  context_tokens: number;
  timeout_seconds: number;
  ai_intent: boolean;
  memory_turns: number;
  summary_every: number;
  cloud_consent: boolean;
  keys?: Record<"openai" | "anthropic", "env" | "file" | null>;
}

export interface AIStatus {
  provider: Exclude<ProviderId, "offline">;
  available: boolean;
  detail: string;
  models: { id: string; name: string; size_bytes: number | null; parameter_size?: string | null; family?: string | null }[];
  selected_model: string;
  selected_model_installed: boolean;
  external: boolean;
}

export interface AIUsage {
  provider: string;
  model: string | null;
  turns: number;
  tokens_in: number;
  tokens_out: number;
}

export interface CreateGameRequest {
  name: string;
  mug: Mug;
  settings: AdventureSettings;
}
