import {
  type ButtonHTMLAttributes,
  type KeyboardEvent,
  type ReactNode,
  useEffect,
  useId,
  useRef,
} from "react";
import { Icon, type IconName } from "./Icon";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-accent text-accent-ink hover:brightness-110 active:brightness-95 shadow-[0_6px_16px_-8px_var(--c-accent)]",
  secondary: "bg-surface text-ink border border-rule hover:bg-surface-2",
  ghost: "bg-transparent text-ink hover:bg-surface-2",
  danger: "bg-bad text-white hover:brightness-110 dark:text-[#1a0d0a]",
};

export function Button({
  variant = "secondary",
  icon,
  children,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; icon?: IconName }) {
  return (
    <button
      type="button"
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 font-ui text-[0.95rem] font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
      {...rest}
    >
      {icon && <Icon name={icon} size={18} />}
      {children}
    </button>
  );
}

export function IconButton({
  icon,
  label,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { icon: IconName; label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={`inline-flex size-11 shrink-0 items-center justify-center rounded-xl text-ink transition hover:bg-surface-2 disabled:opacity-40 ${className}`}
      {...rest}
    >
      <Icon name={icon} size={22} />
    </button>
  );
}

/** Accessible modal built on the native <dialog> (focus trap, Esc, inert background). */
export function Dialog({
  open,
  onClose,
  title,
  children,
  wide = false,
  closeLabel,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  wide?: boolean;
  closeLabel: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dlg = ref.current;
    if (!dlg) return;
    if (open && !dlg.open) {
      if (typeof dlg.showModal === "function") dlg.showModal();
      else dlg.setAttribute("open", "");
    } else if (!open && dlg.open) {
      dlg.close();
    }
  }, [open]);
  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
      className={`card m-auto max-h-[min(92dvh,52rem)] w-[calc(100vw-1.5rem)] overflow-hidden p-0 text-ink backdrop:bg-black/55 backdrop:backdrop-blur-[2px] ${wide ? "max-w-4xl" : "max-w-xl"}`}
    >
      {open && (
        <div className="flex max-h-[min(92dvh,52rem)] flex-col">
          <header className="flex items-center justify-between gap-3 border-b border-rule px-5 py-3">
            <h2 id={titleId} className="font-display text-xl font-semibold">
              {title}
            </h2>
            <IconButton icon="close" label={closeLabel} onClick={onClose} />
          </header>
          <div className="scroll-thin overflow-y-auto px-5 py-4">{children}</div>
        </div>
      )}
    </dialog>
  );
}

export interface TabDef {
  id: string;
  label: string;
  icon?: IconName;
  badge?: number;
}

/** WAI-ARIA tabs with roving focus (←/→/Home/End). */
export function Tabs({
  tabs,
  active,
  onChange,
  label,
  compact = false,
}: {
  tabs: TabDef[];
  active: string;
  onChange: (id: string) => void;
  label: string;
  compact?: boolean;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: KeyboardEvent, index: number) => {
    const moves: Record<string, number> = {
      ArrowRight: (index + 1) % tabs.length,
      ArrowDown: (index + 1) % tabs.length,
      ArrowLeft: (index - 1 + tabs.length) % tabs.length,
      ArrowUp: (index - 1 + tabs.length) % tabs.length,
      Home: 0,
      End: tabs.length - 1,
    };
    const next = moves[e.key];
    if (next === undefined) return;
    e.preventDefault();
    const tab = tabs[next];
    if (tab) {
      onChange(tab.id);
      refs.current[next]?.focus();
    }
  };
  return (
    <div role="tablist" aria-label={label} className={`flex flex-wrap ${compact ? "gap-0.5" : "gap-1"}`}>
      {tabs.map((tab, i) => {
        const selected = tab.id === active;
        return (
          <button
            key={tab.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            role="tab"
            type="button"
            id={`tab-${tab.id}`}
            aria-selected={selected}
            aria-controls={`panel-${tab.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(e) => onKey(e, i)}
            title={tab.label}
            className={`relative inline-flex min-h-11 items-center gap-1.5 rounded-lg ${compact ? "min-w-10 justify-center px-1.5" : "px-2.5"} text-sm font-semibold transition ${
              selected ? "bg-accent-soft text-ink" : "text-muted hover:bg-surface-2 hover:text-ink"
            }`}
          >
            {tab.icon && <Icon name={tab.icon} size={18} />}
            <span className={compact ? "sr-only" : ""}>{tab.label}</span>
            {tab.badge ? (
              <span className={`rounded-full bg-accent px-1.5 text-[0.7rem] leading-5 text-accent-ink ${compact ? "absolute -right-0.5 -top-0.5" : "ml-0.5"}`}>
                {tab.badge}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

export function TabPanel({ id, children }: { id: string; children: ReactNode }) {
  return (
    <div role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`} tabIndex={0} className="outline-none">
      {children}
    </div>
  );
}

/** Labeled gauge. Never relies on color alone: shows the number and an icon. */
export function Meter({
  label,
  value,
  max = 100,
  unit = "%",
  icon,
  tone,
  min = 0,
  hint,
}: {
  label: string;
  value: number;
  max?: number;
  min?: number;
  unit?: string;
  icon: IconName;
  tone: string;
  hint?: string;
}) {
  const pct = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  const shown = Math.round(value);
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuenow={shown}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuetext={`${shown}${unit}${hint ? ` — ${hint}` : ""}`}
      className="space-y-1"
    >
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="flex items-center gap-1.5 font-semibold">
          <Icon name={icon} size={16} className={tone} />
          {label}
        </span>
        <span className="tabular-nums text-muted">
          {shown}
          {unit}
          {hint ? <span className="ml-1 text-xs">· {hint}</span> : null}
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-surface-2 ring-1 ring-rule ring-inset">
        <div
          className="h-full rounded-full bg-current transition-[width] duration-700 ease-out"
          style={{ width: `${pct}%`, color: `var(--c-${tone.replace("text-", "")})` }}
        />
      </div>
    </div>
  );
}

export function Toggle({
  label,
  checked,
  onChange,
  description,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  description?: string;
}) {
  const id = useId();
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <div>
        <label htmlFor={id} className="font-semibold">
          {label}
        </label>
        {description && <p className="text-sm text-muted">{description}</p>}
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 inline-flex h-7 w-12 shrink-0 items-center rounded-full border border-rule transition ${
          checked ? "bg-accent" : "bg-surface-2"
        }`}
      >
        <span
          aria-hidden
          className={`inline-block size-5 rounded-full bg-surface shadow transition ${checked ? "translate-x-6" : "translate-x-1"}`}
        />
      </button>
    </div>
  );
}

export function Field({
  label,
  children,
  help,
  error,
  id,
}: {
  label: string;
  children: ReactNode;
  help?: string;
  error?: string | null;
  id: string;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block font-semibold">
        {label}
      </label>
      {children}
      {help && !error && (
        <p id={`${id}-help`} className="text-sm text-muted">
          {help}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-sm font-semibold text-bad">
          {error}
        </p>
      )}
    </div>
  );
}

export const inputClass =
  "w-full min-h-11 rounded-xl border border-rule bg-surface px-3 py-2 text-ink placeholder:text-muted focus:border-focus";

/** A group of radio "cards" with label + description. */
export function ChoiceGroup<T extends string>({
  legend,
  options,
  value,
  onChange,
  columns = 2,
  multiple = false,
  values = [],
  max,
}: {
  legend: string;
  options: { value: T; label: string; description?: string; swatch?: string }[];
  value?: T;
  onChange: (v: T) => void;
  columns?: number;
  multiple?: boolean;
  values?: T[];
  max?: number;
}) {
  const name = useId();
  return (
    <fieldset className="space-y-2">
      <legend className="mb-1 font-semibold">{legend}</legend>
      <div className={`grid gap-2 ${columns === 3 ? "sm:grid-cols-3" : columns === 4 ? "grid-cols-4 sm:grid-cols-8" : "sm:grid-cols-2"}`}>
        {options.map((opt) => {
          const checked = multiple ? values.includes(opt.value) : value === opt.value;
          const disabled = multiple && !checked && max !== undefined && values.length >= max;
          return (
            <label
              key={opt.value}
              className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition has-[:focus-visible]:outline has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-focus ${
                checked ? "border-accent bg-accent-soft" : "border-rule bg-surface hover:bg-surface-2"
              } ${disabled ? "cursor-not-allowed opacity-50" : ""}`}
              title={opt.swatch ? opt.label : undefined}
            >
              <input
                type={multiple ? "checkbox" : "radio"}
                name={name}
                value={opt.value}
                checked={checked}
                disabled={disabled}
                onChange={() => onChange(opt.value)}
                className={opt.swatch ? "sr-only" : "mt-1 size-4 accent-[var(--c-accent)]"}
              />
              {opt.swatch ? (
                <span className="flex w-full flex-col items-center gap-1">
                  <span
                    aria-hidden
                    className="size-8 rounded-full border-2 border-rule shadow-inner"
                    style={{ background: opt.swatch }}
                  />
                  <span className="sr-only">{opt.label}</span>
                </span>
              ) : (
                <span>
                  <span className="block font-semibold leading-tight">{opt.label}</span>
                  {opt.description && <span className="block text-sm text-muted">{opt.description}</span>}
                </span>
              )}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <span role="status" className="inline-flex items-center gap-2 text-muted">
      <span aria-hidden className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      <span>{label}</span>
    </span>
  );
}
