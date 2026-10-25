import { describe, expect, it } from "vitest";
import { paragraphs, splitDialogue, wrapLines } from "./narration";

const marks = (p: string) => splitDialogue(p).map((s) => `${s.dialogue ? "D" : "N"}:${s.text.trim()}`);

describe("splitDialogue", () => {
  it("handles the Portuguese em-dash speech convention", () => {
    expect(marks("— Voz? — Noir olha para cima. — Tem uma coisa lá.")).toEqual([
      "D:— Voz?",
      "N:— Noir olha para cima.",
      "D:— Tem uma coisa lá.",
    ]);
  });

  it("opens speech after a colon", () => {
    expect(marks("A voz dele chega abafada: — Uma caneca que anda.")).toEqual([
      "N:A voz dele chega abafada:",
      "D:— Uma caneca que anda.",
    ]);
  });

  it("keeps mid-sentence parenthetical dashes as narration", () => {
    expect(marks("O mundo gira — toalha, cadeira, chão — e você aterrissa.")).toEqual([
      "N:O mundo gira — toalha, cadeira, chão — e você aterrissa.",
    ]);
  });

  it("detects quoted speech", () => {
    expect(marks('Noir says, "Hello, crockery." Then he yawns.')).toEqual([
      "N:Noir says,",
      'D:"Hello, crockery."',
      "N:Then he yawns.",
    ]);
  });
});

describe("text helpers", () => {
  it("splits paragraphs on blank lines", () => {
    expect(paragraphs("a\n\n\nb\n\n")).toEqual(["a", "b"]);
  });

  it("wraps lines by measured width", () => {
    expect(wrapLines((s) => s.length, "um dois três quatro", 8)).toEqual(["um dois", "três", "quatro"]);
  });
});
