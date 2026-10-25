import { memo, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { CheckView, EventView } from "../../api/types";
import { type MessageKey, useT } from "../../i18n";
import { type FeedEntry, useGame } from "../../store/game";
import { TEXT_SPEED_CPS, prefersReducedMotion, usePrefs } from "../../store/prefs";
import { Icon } from "../ui/Icon";
import { paragraphs, splitDialogue, wrapLines } from "./narration";

export const SKIP_EVENT = "caneca:skip";

export function NarrativeFeed() {
  const { t } = useT();
  const feed = useGame((s) => s.feed);
  const hasMore = useGame((s) => s.hasMore);
  const loadingHistory = useGame((s) => s.loadingHistory);
  const loadOlder = useGame((s) => s.loadOlder);
  const narration = useGame((s) => s.narration);
  const scroller = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  const [showJump, setShowJump] = useState(false);
  const lastLength = feed.length ? feed[feed.length - 1]?.text.length ?? 0 : 0;

  const onScroll = () => {
    const el = scroller.current;
    if (!el) return;
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < 140;
    pinned.current = near;
    setShowJump(!near);
  };

  useLayoutEffect(() => {
    const el = scroller.current;
    if (el && pinned.current) el.scrollTop = el.scrollHeight;
  }, [feed.length, lastLength]);

  useEffect(() => {
    const el = scroller.current;
    const content = el?.firstElementChild;
    if (!el || !content || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => {
      if (pinned.current) el.scrollTop = el.scrollHeight;
    });
    observer.observe(content);
    return () => observer.disconnect();
  }, []);

  const jump = () => {
    const el = scroller.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    pinned.current = true;
    setShowJump(false);
  };

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={scroller}
        onScroll={onScroll}
        className="scroll-thin h-full overflow-y-auto overscroll-contain px-4 pb-6 pt-4 sm:px-8"
      >
        <div
          role="log"
          aria-label={t("a11y.narrativeLog")}
          aria-live="off"
          className="mx-auto flex max-w-[44rem] flex-col gap-5"
        >
          {hasMore && (
            <button
              type="button"
              onClick={() => void loadOlder()}
              disabled={loadingHistory}
              className="mx-auto min-h-11 rounded-full px-4 text-sm font-semibold text-muted hover:bg-surface-2"
            >
              {loadingHistory ? t("a11y.loading") : t("game.loadOlder")}
            </button>
          )}
          {feed.length === 0 && <p className="text-center text-muted">{t("game.nothingYet")}</p>}
          {feed.map((entry, i) => (
            <FeedItem key={entry.id} entry={entry} first={i === 0 || entry.kind === "intro"} />
          ))}
        </div>
      </div>
      {/* Screen readers get each finished narration once, not every streamed token. */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {narration ? `${t("a11y.newNarration")}: ${narration.text}` : ""}
      </div>
      {showJump && (
        <button
          type="button"
          onClick={jump}
          aria-label={t("a11y.newNarration")}
          className="card absolute bottom-3 left-1/2 inline-flex size-11 -translate-x-1/2 items-center justify-center rounded-full"
        >
          <Icon name="chevronDown" />
        </button>
      )}
    </div>
  );
}

const FeedItem = memo(function FeedItem({ entry, first }: { entry: FeedEntry; first: boolean }) {
  if (entry.kind === "player") return <PlayerLine text={entry.text} />;
  return <NarrationBlock entry={entry} dropCap={first && entry.kind === "intro"} />;
});

function PlayerLine({ text }: { text: string }) {
  const { t } = useT();
  return (
    <p className="animate-rise ml-auto max-w-[85%] rounded-2xl rounded-br-md border border-rule bg-surface-2 px-4 py-2 text-[0.98rem] text-player italic">
      <span className="sr-only">{t("game.you")}: </span>
      <span aria-hidden className="mr-1.5 font-semibold not-italic">›</span>
      {text}
    </p>
  );
}

function useTypewriter(text: string, active: boolean): [number, () => void] {
  const speed = usePrefs((s) => s.textSpeed);
  const motion = usePrefs((s) => s.motion);
  const instant = !active || speed === "instant" || prefersReducedMotion(motion);
  const [progress, setProgress] = useState({ text, n: 0 });
  const shown = instant ? text.length : progress.text === text ? progress.n : 0;

  useEffect(() => {
    if (instant) return;
    const cps = TEXT_SPEED_CPS[speed];
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const n = Math.min(text.length, Math.floor(((now - start) / 1000) * cps));
      setProgress({ text, n });
      if (n < text.length) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    const skip = () => {
      cancelAnimationFrame(raf);
      setProgress({ text, n: text.length });
    };
    window.addEventListener(SKIP_EVENT, skip);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener(SKIP_EVENT, skip);
    };
  }, [text, instant, speed]);

  return [shown, () => setProgress({ text, n: text.length })];
}

function NarrationBlock({ entry, dropCap }: { entry: FeedEntry; dropCap: boolean }) {
  const { t } = useT();
  const showChecks = usePrefs((s) => s.showChecks);
  const [shown, revealAll] = useTypewriter(entry.text, Boolean(entry.animate));
  const visible = entry.text.slice(0, shown);
  const typing = shown < entry.text.length;
  const waiting = entry.streaming && !entry.text;

  return (
    <article
      className="animate-rise group"
      onClick={typing ? revealAll : undefined}
      aria-busy={entry.streaming || typing ? true : undefined}
    >
      {waiting ? (
        <WritingIndicator />
      ) : (
        <div className={`prose-narrative ${entry.streaming || typing ? "stream-caret" : ""}`}>
          {paragraphs(visible).map((p, i) => (
            <p key={i} className={dropCap && i === 0 ? "drop-cap" : undefined}>
              {splitDialogue(p).map((seg, j) =>
                seg.dialogue ? (
                  <span key={j} className="dialogue">
                    {seg.text}
                  </span>
                ) : (
                  <span key={j}>{seg.text}</span>
                ),
              )}
            </p>
          ))}
        </div>
      )}
      {!entry.streaming && !typing && (
        <footer className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
          {entry.check && showChecks && <CheckBadge check={entry.check} />}
          {entry.events?.map((ev, i) => <EventChip key={i} ev={ev} />)}
          {entry.source && entry.source !== "engine" && (
            <span className="rounded-full border border-rule px-2 py-0.5 text-muted">
              {t(
                ({ ai: "game.badgeAi", fallback: "game.badgeFallback", cancelled: "game.badgeCancelled" } as const)[
                  entry.source
                ],
              )}
            </span>
          )}
          {entry.text && <EntryActions text={entry.text} />}
        </footer>
      )}
    </article>
  );
}

function WritingIndicator() {
  const { t } = useT();
  return (
    <p className="flex items-center gap-2 font-read text-muted italic">
      <Icon name="feather" size={18} className="animate-pulse" />
      {t("game.narrating")}
    </p>
  );
}

const STAT_KEYS: Record<string, MessageKey> = {
  temperature: "stats.temperature",
  coffee: "stats.coffee",
  integrity: "stats.integrity",
  energy: "stats.energy",
  courage: "stats.courage",
  creativity: "stats.creativity",
};

function CheckBadge({ check }: { check: CheckView }) {
  const { t } = useT();
  const good = check.outcome === "success" || check.outcome === "critical";
  const stat = STAT_KEYS[check.stat] ? t(STAT_KEYS[check.stat]!) : check.stat;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-semibold ${good ? "border-good text-good" : "border-bad text-bad"}`}
      title={t("game.check", { stat, roll: check.roll, mod: check.modifier, total: check.total, dc: check.dc })}
    >
      <Icon name="dice" size={14} />
      <span className="sr-only">{t("game.check", { stat, roll: check.roll, mod: check.modifier, total: check.total, dc: check.dc })}</span>
      <span aria-hidden>
        {check.roll}
        {check.modifier >= 0 ? "+" : ""}
        {check.modifier} vs {check.dc} · {t(`game.outcome.${check.outcome}`)}
      </span>
    </span>
  );
}

const STAT_UNITS: Record<string, string> = { temperature: "°C", coffee: "%", integrity: "%", energy: "%" };

function EventChip({ ev }: { ev: EventView }) {
  const { t } = useT();
  let text: string | null = null;
  let tone = "text-muted border-rule";
  if (ev.kind === "stat" && typeof ev.delta === "number" && ev.stat) {
    const key = STAT_KEYS[ev.stat];
    const sign = ev.delta > 0 ? "+" : "−";
    text = `${key ? t(key) : ev.stat} ${sign}${Math.abs(Math.round(ev.delta))}${STAT_UNITS[ev.stat] ?? ""}`;
    tone = ev.delta > 0 ? "text-good border-good" : "text-bad border-bad";
    if (ev.stat === "temperature") tone = ev.delta > 0 ? "text-hot border-hot" : "text-cold border-cold";
  } else if (ev.kind === "xp" && ev.amount) {
    text = t("game.eventLabels.xp", { amount: ev.amount });
    tone = "text-accent border-accent";
  } else if ((ev.kind === "item_gained" || ev.kind === "item_lost" || ev.kind === "moved") && ev.label) {
    text = t(`game.eventLabels.${ev.kind}`, { label: ev.label });
  } else if (ev.kind === "relationship" && ev.label && typeof ev.delta === "number") {
    text = t("game.eventLabels.relationship", { label: ev.label, delta: `${ev.delta > 0 ? "+" : ""}${ev.delta}` });
    tone = ev.delta > 0 ? "text-good border-good" : "text-bad border-bad";
  }
  if (!text) return null;
  return <span className={`rounded-full border px-2 py-0.5 font-semibold ${tone}`}>{text}</span>;
}

function EntryActions({ text }: { text: string }) {
  const { t } = useT();
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable */
    }
  };
  return (
    <span className="ml-auto flex gap-1 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100 [@media(hover:none)]:opacity-100">
      <button
        type="button"
        onClick={copy}
        className="inline-flex min-h-8 items-center gap-1 rounded-md px-2 text-muted hover:bg-surface-2 hover:text-ink"
      >
        <Icon name="copy" size={14} />
        {copied ? t("game.copied") : t("game.copy")}
      </button>
      <button
        type="button"
        onClick={() => downloadCard(text)}
        className="inline-flex min-h-8 items-center gap-1 rounded-md px-2 text-muted hover:bg-surface-2 hover:text-ink"
      >
        <Icon name="image" size={14} />
        {t("game.shareCard")}
      </button>
    </span>
  );
}

/** Renders a passage into a shareable PNG card, locally. Nothing is uploaded. */
function downloadCard(text: string) {
  const canvas = document.createElement("canvas");
  canvas.width = 1080;
  canvas.height = 1350;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
  grad.addColorStop(0, "#1a2030");
  grad.addColorStop(1, "#2b1f17");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#e0a066";
  ctx.lineWidth = 4;
  ctx.strokeRect(48, 48, canvas.width - 96, canvas.height - 96);
  ctx.fillStyle = "#e0a066";
  ctx.font = "600 44px 'Fraunces Variable', Georgia, serif";
  ctx.fillText("☕ Caneca Quest", 96, 150);
  ctx.fillStyle = "#efe6d8";
  ctx.font = "34px 'Literata Variable', Georgia, serif";
  const clipped = text.length > 900 ? `${text.slice(0, 900)}…` : text;
  const lines = wrapLines((s) => ctx.measureText(s).width, clipped, canvas.width - 192);
  lines.slice(0, 26).forEach((line, i) => ctx.fillText(line, 96, 240 + i * 46));
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "caneca-quest.png";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }, "image/png");
}
