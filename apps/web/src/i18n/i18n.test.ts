import { describe, expect, it } from "vitest";
import { en } from "./en";
import { interpolate, relativeTime, translate } from "./index";
import { ptBR } from "./pt-BR";

function shape(node: unknown, path = ""): string[] {
  if (Array.isArray(node)) return [`${path}[]`];
  if (node && typeof node === "object") {
    return Object.entries(node as Record<string, unknown>).flatMap(([k, v]) => shape(v, path ? `${path}.${k}` : k));
  }
  return [path];
}

function leaves(node: unknown, path = ""): [string, string][] {
  if (typeof node === "string") return [[path, node]];
  if (Array.isArray(node)) return node.flatMap((v, i) => leaves(v, `${path}[${i}]`));
  if (node && typeof node === "object") {
    return Object.entries(node as Record<string, unknown>).flatMap(([k, v]) => leaves(v, path ? `${path}.${k}` : k));
  }
  return [];
}

describe("i18n dictionaries", () => {
  it("have exactly the same keys in every language", () => {
    expect(shape(en).sort()).toEqual(shape(ptBR).sort());
  });

  it("have no empty strings (except intentionally empty descriptions)", () => {
    for (const dict of [ptBR, en]) {
      const empty = leaves(dict).filter(([p, v]) => !v.trim() && !p.startsWith("options.language"));
      expect(empty).toEqual([]);
    }
  });

  it("use the same placeholders in both languages", () => {
    const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    const enLeaves = new Map(leaves(en));
    for (const [path, value] of leaves(ptBR)) {
      const other = enLeaves.get(path);
      if (other !== undefined) expect(placeholders(other), path).toEqual(placeholders(value));
    }
  });
});

describe("translate", () => {
  it("interpolates params and keeps unknown placeholders", () => {
    expect(interpolate("Nível {n} de {x}", { n: 2 })).toBe("Nível 2 de {x}");
    expect(translate("en", "stats.level", { n: 3 })).toBe("Level 3");
    expect(translate("pt-BR", "stats.level", { n: 3 })).toBe("Nível 3");
  });

  it("formats relative times", () => {
    const now = Date.parse("2026-01-01T12:00:00Z");
    expect(relativeTime("pt-BR", "2026-01-01T11:55:00Z", now)).toBe("há 5 min");
    expect(relativeTime("en", "2025-12-30T12:00:00Z", now)).toBe("2 days ago");
  });
});
