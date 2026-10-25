import { usePrefs } from "../store/prefs";
import { en } from "./en";
import { ptBR, type Dictionary } from "./pt-BR";

export type Lang = "pt-BR" | "en";
export const LANGS: Lang[] = ["pt-BR", "en"];
const DICTS: Record<Lang, Dictionary> = { "pt-BR": ptBR, en };

/** Dotted paths to string leaves, e.g. "game.send". */
type Leaves<T, P extends string = ""> = {
  [K in keyof T & string]: T[K] extends string
    ? `${P}${K}`
    : T[K] extends readonly unknown[]
      ? never
      : Leaves<T[K], `${P}${K}.`>;
}[keyof T & string];

export type MessageKey = Leaves<Dictionary>;
export type Params = Record<string, string | number>;

export function detectLanguage(): Lang {
  const nav = typeof navigator !== "undefined" ? navigator.language : "pt-BR";
  return nav.toLowerCase().startsWith("pt") ? "pt-BR" : "en";
}

function lookup(dict: Dictionary, key: string): unknown {
  return key.split(".").reduce<unknown>((node, part) => {
    if (node && typeof node === "object") return (node as Record<string, unknown>)[part];
    return undefined;
  }, dict);
}

export function interpolate(template: string, params?: Params): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, name: string) =>
    name in params ? String(params[name]) : `{${name}}`,
  );
}

export function translate(lang: Lang, key: MessageKey, params?: Params): string {
  const value = lookup(DICTS[lang], key) ?? lookup(ptBR, key);
  return typeof value === "string" ? interpolate(value, params) : key;
}

export function dictionary(lang: Lang): Dictionary {
  return DICTS[lang];
}

/** Translator bound to the current UI language. */
export function useT() {
  const lang = usePrefs((s) => s.language);
  const t = (key: MessageKey, params?: Params) => translate(lang, key, params);
  return { t, lang, d: DICTS[lang] };
}

/** Option label/description pairs (e.g. options.tone.mystery). */
export function optionText(
  lang: Lang,
  group: keyof Dictionary["options"],
  value: string,
): { label: string; description: string } {
  const table = DICTS[lang].options[group] as Record<string, readonly string[]>;
  const pair = table[value] ?? [value, ""];
  return { label: pair[0] ?? value, description: pair[1] ?? "" };
}

export function relativeTime(lang: Lang, iso: string, now = Date.now()): string {
  const diff = Math.max(0, now - new Date(iso).getTime()) / 60000;
  if (diff < 1) return translate(lang, "time.now");
  if (diff < 60) return translate(lang, "time.minutes", { n: Math.floor(diff) });
  if (diff < 60 * 24) return translate(lang, "time.hours", { n: Math.floor(diff / 60) });
  return translate(lang, "time.days", { n: Math.floor(diff / 1440) });
}
