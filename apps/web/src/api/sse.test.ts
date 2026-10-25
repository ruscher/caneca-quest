import { describe, expect, it } from "vitest";
import { SseParser, readSse } from "./sse";

describe("SseParser", () => {
  it("parses events split across arbitrary chunks", () => {
    const p = new SseParser();
    const raw = 'event: outcome\ndata: {"a":1}\n\nevent: delta\ndata: {"text":"Olá"}\n\n';
    const events = [];
    for (const ch of raw) events.push(...p.push(ch));
    expect(events).toEqual([
      { event: "outcome", data: '{"a":1}' },
      { event: "delta", data: '{"text":"Olá"}' },
    ]);
  });

  it("joins multi-line data, ignores comments and normalizes CRLF", () => {
    const p = new SseParser();
    const events = p.push(": ping\r\nevent: done\r\ndata: linha 1\r\ndata: linha 2\r\n\r\n");
    expect(events).toEqual([{ event: "done", data: "linha 1\nlinha 2" }]);
  });

  it("defaults the event name and flushes a trailing block", () => {
    const p = new SseParser();
    expect(p.push("data: x")).toEqual([]);
    expect(p.flush()).toEqual([{ event: "message", data: "x" }]);
  });

  it("reads a ReadableStream body", async () => {
    const enc = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
      start(c) {
        c.enqueue(enc.encode("event: a\nda"));
        c.enqueue(enc.encode("ta: 1\n\nevent: b\ndata: 2\n\n"));
        c.close();
      },
    });
    const got = [];
    for await (const ev of readSse(body)) got.push(ev.event + ev.data);
    expect(got).toEqual(["a1", "b2"]);
  });
});
