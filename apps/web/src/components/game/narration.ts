export interface Segment {
  text: string;
  dialogue: boolean;
}

const OPENS_AFTER = /[.!?:…"”)]$/;

/**
 * Splits a paragraph into narration and dialogue segments.
 *
 * Portuguese uses the em dash for speech: "— Fala — disse ele. — Mais fala." A dash opens
 * speech at the start of a paragraph or right after sentence punctuation; inside speech,
 * the next dash closes it. Mid-sentence dashes ("o mundo gira — toalha, chão — e você")
 * are parenthetical and stay narration. Quoted speech ("…" / “…”) is handled too.
 */
export function splitDialogue(paragraph: string): Segment[] {
  const out: Segment[] = [];
  let dialogue = false;
  let start = 0;
  for (let i = 0; i < paragraph.length; i++) {
    if (paragraph[i] !== "—") continue;
    const before = paragraph.slice(0, i).trimEnd();
    const opens: boolean = !dialogue && (before === "" || OPENS_AFTER.test(before));
    const closes = dialogue;
    if (!opens && !closes) continue;
    if (i > start) out.push({ text: paragraph.slice(start, i), dialogue });
    dialogue = opens;
    start = i;
  }
  if (start < paragraph.length) out.push({ text: paragraph.slice(start), dialogue });
  return merge(out.flatMap((s) => (s.dialogue ? [s] : splitQuotes(s.text))));
}

function splitQuotes(text: string): Segment[] {
  const out: Segment[] = [];
  const re = /("[^"]+"|“[^”]+”)/g;
  let last = 0;
  for (const m of text.matchAll(re)) {
    const idx = m.index ?? 0;
    if (idx > last) out.push({ text: text.slice(last, idx), dialogue: false });
    out.push({ text: m[0], dialogue: true });
    last = idx + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last), dialogue: false });
  return out;
}

function merge(segments: Segment[]): Segment[] {
  const out: Segment[] = [];
  for (const s of segments) {
    if (!s.text) continue;
    const prev = out[out.length - 1];
    if (prev && prev.dialogue === s.dialogue) prev.text += s.text;
    else out.push({ ...s });
  }
  return out;
}

export function paragraphs(text: string): string[] {
  return text
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);
}

/** Wraps text for canvas rendering. */
export function wrapLines(measure: (s: string) => number, text: string, width: number): string[] {
  const lines: string[] = [];
  for (const para of text.split("\n")) {
    let line = "";
    for (const word of para.split(/\s+/)) {
      const next = line ? `${line} ${word}` : word;
      if (measure(next) > width && line) {
        lines.push(line);
        line = word;
      } else {
        line = next;
      }
    }
    lines.push(line);
  }
  return lines;
}
