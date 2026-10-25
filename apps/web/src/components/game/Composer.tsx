import { type FormEvent, type KeyboardEvent, useEffect, useId, useRef, useState } from "react";
import type { Suggestion } from "../../api/types";
import { useT } from "../../i18n";
import { useGame } from "../../store/game";
import { Icon } from "../ui/Icon";
import { Spinner } from "../ui/primitives";
import { SKIP_EVENT } from "./NarrativeFeed";

const MAX = 500;

const KIND_ICON = {
  story: "sparkle",
  talk: "users",
  move: "compass",
  item: "bag",
  examine: "info",
  care: "flame",
  action: "play",
} as const;

export function Composer() {
  const { t } = useT();
  const phase = useGame((s) => s.phase);
  const game = useGame((s) => s.game);
  const act = useGame((s) => s.act);
  const cancel = useGame((s) => s.cancel);
  const history = useGame((s) => s.commandHistory);
  const [text, setText] = useState("");
  const [historyIndex, setHistoryIndex] = useState(-1);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const inputId = useId();
  const busy = phase !== "idle";
  const finished = Boolean(game?.ending || game?.defeated);
  const suggestions = game?.suggestions ?? [];
  const narrow = typeof window !== "undefined" && window.innerWidth < 640;

  const submit = (value: string, suggestion?: Suggestion) => {
    if (busy || finished || !value.trim()) return;
    void act(value, suggestion ?? null);
    setText("");
    setHistoryIndex(-1);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit(text);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit(text);
    } else if (e.key === "ArrowUp" && (text === "" || historyIndex >= 0) && history.length) {
      e.preventDefault();
      const next = Math.min(history.length - 1, historyIndex + 1);
      setHistoryIndex(next);
      setText(history[next] ?? "");
    } else if (e.key === "ArrowDown" && historyIndex >= 0) {
      e.preventDefault();
      const next = historyIndex - 1;
      setHistoryIndex(next);
      setText(next >= 0 ? (history[next] ?? "") : "");
    }
  };

  // Auto-grow the textarea up to ~4 lines.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
  }, [text]);

  // Global shortcuts: Ctrl+K focus, Esc skip/stop, Alt+1..6 suggestions.
  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      } else if (e.key === "Escape") {
        if (document.querySelector("dialog[open]")) return;
        window.dispatchEvent(new Event(SKIP_EVENT));
        if (useGame.getState().phase !== "idle") cancel();
      } else if (e.altKey && /^[1-6]$/.test(e.key)) {
        const sug = suggestions[Number(e.key) - 1];
        if (sug) {
          e.preventDefault();
          submit(sug.label, sug);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="border-t border-rule bg-bg/85 px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur-md sm:px-6">
      <div className="mx-auto max-w-[44rem] space-y-2.5">
        {suggestions.length > 0 && !finished && (
          <div
            role="group"
            aria-label={t("game.suggestions")}
            className="scroll-thin -mx-3 flex snap-x gap-1.5 overflow-x-auto px-3 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0 sm:pb-0"
          >
            {suggestions.map((sug, i) => (
              <button
                key={`${sug.verb}-${sug.target}-${sug.interaction}-${i}`}
                type="button"
                disabled={busy}
                onClick={() => submit(sug.label, sug)}
                aria-keyshortcuts={`Alt+${i + 1}`}
                className="inline-flex min-h-10 shrink-0 snap-start items-center gap-1.5 rounded-full border border-rule bg-surface px-3 py-1.5 text-left text-sm leading-tight transition hover:border-accent hover:bg-accent-soft disabled:opacity-50 max-sm:max-w-[80vw]"
              >
                <Icon name={KIND_ICON[sug.kind as keyof typeof KIND_ICON] ?? "play"} size={15} className="shrink-0 text-accent" />
                {sug.label}
              </button>
            ))}
          </div>
        )}

        <form onSubmit={onSubmit} className="flex items-end gap-2">
          <div className="min-w-0 flex-1">
            <label htmlFor={inputId} className="sr-only">
              {t("game.actionLabel")}
            </label>
            <textarea
              id={inputId}
              ref={inputRef}
              rows={1}
              maxLength={MAX}
              value={text}
              disabled={finished}
              onChange={(e) => {
                setText(e.target.value);
                setHistoryIndex(-1);
              }}
              onKeyDown={onKeyDown}
              placeholder={narrow ? t("game.placeholderShort") : t("game.placeholder")}
              enterKeyHint="send"
              autoComplete="off"
              spellCheck
              aria-describedby={`${inputId}-hint`}
              className="block max-h-32 min-h-12 w-full resize-none rounded-2xl border border-rule bg-surface px-4 py-3 font-read text-[1.02rem] text-ink shadow-inner placeholder:text-muted focus:border-focus"
            />
          </div>
          {busy ? (
            <button
              type="button"
              onClick={cancel}
              aria-label={t("game.cancel")}
              className="inline-flex min-h-12 shrink-0 items-center gap-2 rounded-2xl border border-rule bg-surface px-4 font-semibold text-ink hover:bg-surface-2"
            >
              <Icon name="stop" size={18} />
              <span aria-hidden className="hidden sm:inline">
                {t("game.cancel")}
              </span>
            </button>
          ) : (
            <button
              type="submit"
              aria-label={t("game.send")}
              disabled={!text.trim() || finished}
              className="inline-flex min-h-12 shrink-0 items-center gap-2 rounded-2xl bg-accent px-4 font-semibold text-accent-ink transition hover:brightness-110 disabled:opacity-50"
            >
              <Icon name="send" size={18} />
              <span aria-hidden className="hidden sm:inline">
                {t("game.send")}
              </span>
            </button>
          )}
        </form>
        <div id={`${inputId}-hint`} className="flex min-h-5 items-center justify-between gap-2 text-xs text-muted">
          {busy ? (
            <Spinner label={phase === "resolving" ? t("game.resolving") : t("game.narrating")} />
          ) : (
            <span className="hidden md:inline">{t("game.shortcutsHint")}</span>
          )}
          {text.length > MAX - 100 && (
            <span aria-live="polite" className="ml-auto tabular-nums">
              {t("game.charsLeft", { n: MAX - text.length })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
