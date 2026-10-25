import type { GameView } from "../api/types";

export function gameView(overrides: Partial<GameView> = {}): GameView {
  return {
    id: "g1",
    name: "Teste",
    status: "active",
    version: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    turn: 0,
    language: "pt-BR",
    settings: { tone: "balanced", difficulty: "adventure", narrative_length: "normal", language: "pt-BR" },
    mug: { name: "Aurora", color: "#f4efe6", style: "classic", material: "porcelain", drink: "black_coffee", personality: "optimistic", traits: [] },
    chapter: { number: 1, title: "Capítulo 1 — O Despertar" },
    region: { id: "cafeteria", name: "A Cafeteria Esquecida", palette: "cafe" },
    clock: "21:40",
    stats: { temperature: 80, coffee: 75, integrity: 95, energy: 100, courage: 50, creativity: 50, xp: 0, level: 1, xp_level_start: 0, xp_next: 100 },
    statuses: [{ id: "hot", label: "quente" }],
    abilities: [],
    location: {
      id: "mesa_principal", name: "Mesa perto da janela", short: "A mesa.", description: "Uma mesa.", region: "cafeteria",
      dark: false, heat: false, ambient_temp: 17, features: [], items: [], npcs: [], exits: [],
    },
    inventory: [],
    capacity: { used: 0, max: 5 },
    quests: [],
    relationships: [],
    map: { regions: [], nodes: [], edges: [] },
    achievements: [],
    codex: [],
    suggestions: [
      { label: "Gritar por ajuda", verb: "shout", target: null, item: null, kind: "story", interaction: "mesa_gritar" },
      { label: "Olhar ao redor", verb: "look", target: null, item: null, kind: "examine", interaction: null },
    ],
    ending: null,
    defeated: false,
    ...overrides,
  };
}

export function sseResponse(events: [string, unknown][], status = 200): Response {
  const body = events.map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`).join("");
  const bytes = new TextEncoder().encode(body);
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(bytes);
      controller.close();
    },
  });
  return new Response(stream, { status, headers: { "content-type": "text/event-stream" } });
}

export function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });
}
