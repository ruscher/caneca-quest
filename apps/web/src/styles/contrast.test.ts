/// <reference types="node" />
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// Parses the design tokens straight from the stylesheet so the test follows real values.
const css = readFileSync(resolve(__dirname, "index.css"), "utf8");

function block(selector: string): Record<string, string> {
  const start = css.indexOf(`${selector} {`);
  const body = css.slice(start, css.indexOf("}", start));
  return Object.fromEntries([...body.matchAll(/--(c-[\w-]+):\s*(#[0-9a-f]{6})/gi)].map((m) => [m[1]!, m[2]!]));
}

function luminance(hex: string): number {
  const n = parseInt(hex.slice(1), 16);
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * ch[0]! + 0.7152 * ch[1]! + 0.0722 * ch[2]!;
}

function ratio(a: string, b: string): number {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1! + 0.05) / (l2! + 0.05);
}

const TEXT_ON = ["c-ink", "c-muted", "c-accent", "c-dialogue", "c-player", "c-good", "c-bad", "c-warn", "c-cold", "c-hot"];
const BACKGROUNDS = ["c-bg", "c-surface", "c-surface-2"];

describe.each([
  ["light", ":root"],
  ['dark', '[data-theme="dark"]'],
])("WCAG AA contrast — %s theme", (_name, selector) => {
  const tokens = block(selector);
  for (const fg of TEXT_ON) {
    for (const bg of BACKGROUNDS) {
      it(`${fg} on ${bg} ≥ 4.5:1`, () => {
        expect(ratio(tokens[fg]!, tokens[bg]!)).toBeGreaterThanOrEqual(4.5);
      });
    }
  }
  it("accent button text ≥ 4.5:1", () => {
    expect(ratio(tokens["c-accent-ink"]!, tokens["c-accent"]!)).toBeGreaterThanOrEqual(4.5);
  });
  it("focus ring ≥ 3:1 against the page", () => {
    expect(ratio(tokens["c-focus"]!, tokens["c-bg"]!)).toBeGreaterThanOrEqual(3);
  });
});
