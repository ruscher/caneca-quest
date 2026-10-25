import { type MessageKey, useT } from "../../i18n";
import { useGame } from "../../store/game";
import { Icon, type IconName } from "./Icon";

const ICONS: Record<string, IconName> = {
  info: "info",
  success: "sparkle",
  warning: "info",
  error: "close",
  achievement: "star",
  quest: "scroll",
};

/** Toast text is either "raw:<already translated text>" or an error code (errors.<code>). */
export function Toasts() {
  const { t } = useT();
  const toasts = useGame((s) => s.toasts);
  const dismiss = useGame((s) => s.dismissToast);
  const text = (raw: string) => {
    if (raw.startsWith("raw:")) return raw.slice(4);
    const key = `errors.${raw}` as MessageKey;
    const translated = t(key);
    return translated === key ? t("errors.generic") : translated;
  };
  const polite = toasts.filter((x) => x.kind !== "error");
  const assertive = toasts.filter((x) => x.kind === "error");
  const render = (list: typeof toasts) =>
    list.map((toast) => (
      <li
        key={toast.id}
        className={`card animate-rise pointer-events-auto flex items-start gap-2 px-4 py-3 text-sm ${
          toast.kind === "error" ? "border-bad" : toast.kind === "achievement" ? "border-accent" : ""
        }`}
      >
        <Icon name={ICONS[toast.kind] ?? "info"} size={18} className={toast.kind === "error" ? "text-bad" : "text-accent"} />
        <span className="flex-1">{text(toast.text)}</span>
        <button
          type="button"
          onClick={() => dismiss(toast.id)}
          aria-label={t("a11y.close")}
          className="-m-1 inline-flex size-8 items-center justify-center rounded-md text-muted hover:text-ink"
        >
          <Icon name="close" size={16} />
        </button>
      </li>
    ));
  return (
    <div className="pointer-events-none fixed inset-x-0 top-16 z-50 mx-auto flex max-w-md flex-col gap-2 px-3">
      <ul aria-live="polite" className="flex flex-col gap-2">
        {render(polite)}
      </ul>
      <ul aria-live="assertive" className="flex flex-col gap-2">
        {render(assertive)}
      </ul>
    </div>
  );
}
