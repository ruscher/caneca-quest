import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { gameView, jsonResponse, sseResponse } from "../test/fixtures";
import { useGame } from "./game";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  useGame.setState({ game: gameView(), feed: [], phase: "idle", toasts: [], commandHistory: [], screen: "game" });
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("act()", () => {
  it("streams a turn: outcome → deltas → done", async () => {
    const after = gameView({ turn: 1, clock: "21:43" });
    fetchMock.mockResolvedValueOnce(
      sseResponse([
        ["outcome", { turn: 1, intent: { verb: "look" }, check: null, success: true, fallback: "Texto do motor.", events: [], view: after }],
        ["delta", { text: "A chuva " }],
        ["delta", { text: "cai." }],
        ["done", { narration: "A chuva cai.", source: "ai" }],
      ]),
    );
    await useGame.getState().act("olhar ao redor");
    const s = useGame.getState();
    expect(s.phase).toBe("idle");
    expect(s.game?.turn).toBe(1);
    expect(s.feed.map((e) => e.kind)).toEqual(["player", "narration"]);
    expect(s.feed[1]).toMatchObject({ text: "A chuva cai.", source: "ai", streaming: false });
    expect(s.commandHistory[0]).toBe("olhar ao redor");
    const [, init] = fetchMock.mock.calls[0]!;
    expect(JSON.parse(String(init?.body))).toEqual({ text: "olhar ao redor", expected_turn: 0 });
  });

  it("sends the suggestion intent", async () => {
    fetchMock.mockResolvedValueOnce(sseResponse([["done", { narration: "x", source: "engine" }]]));
    const sug = gameView().suggestions[0]!;
    await useGame.getState().act(sug.label, sug);
    const body = JSON.parse(String(fetchMock.mock.calls[0]![1]?.body));
    expect(body.intent).toEqual({ verb: "shout", target: null, item: null, interaction: "mesa_gritar" });
  });

  it("ignores empty input and concurrent submissions", async () => {
    await useGame.getState().act("   ");
    useGame.setState({ phase: "narrating" });
    await useGame.getState().act("olhar");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("drops the optimistic entry and toasts when the server refuses the turn", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ error: { code: "turn_in_progress" } }, 409));
    await useGame.getState().act("olhar");
    const s = useGame.getState();
    expect(s.feed).toEqual([]);
    expect(s.toasts.at(-1)).toMatchObject({ kind: "error", text: "turn_in_progress" });
    expect(s.phase).toBe("idle");
  });

  it("keeps the engine text when the narration is cancelled", async () => {
    const view = gameView({ turn: 1 });
    fetchMock.mockImplementationOnce(async (_url, init) => {
      const signal = init?.signal as AbortSignal;
      const enc = new TextEncoder();
      const body = new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(enc.encode(`event: outcome\ndata: ${JSON.stringify({ turn: 1, intent: {}, check: null, success: true, fallback: "Texto oficial.", events: [], view })}\n\n`));
          signal.addEventListener("abort", () => controller.error(new DOMException("aborted", "AbortError")));
        },
      });
      return new Response(body, { headers: { "content-type": "text/event-stream" } });
    });
    fetchMock.mockResolvedValue(jsonResponse({ cancelled: true }));
    const running = useGame.getState().act("olhar");
    await vi.waitFor(() => expect(useGame.getState().phase).toBe("narrating"));
    useGame.getState().cancel();
    await running;
    const entry = useGame.getState().feed.at(-1)!;
    expect(entry).toMatchObject({ source: "cancelled", text: "Texto oficial.", streaming: false });
  });

  it("surfaces AI warnings as toasts without failing the turn", async () => {
    fetchMock.mockResolvedValueOnce(
      sseResponse([
        ["outcome", { turn: 1, intent: {}, check: null, success: true, fallback: "F.", events: [], view: gameView({ turn: 1 }) }],
        ["warning", { code: "ai_timeout" }],
        ["done", { narration: "F.", source: "fallback" }],
      ]),
    );
    await useGame.getState().act("olhar");
    expect(useGame.getState().toasts.some((t) => t.text === "ai_timeout")).toBe(true);
    expect(useGame.getState().feed.at(-1)?.source).toBe("fallback");
  });
});
