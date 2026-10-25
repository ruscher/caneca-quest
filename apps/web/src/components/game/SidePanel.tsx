import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { GameView, JournalEntry, Memories } from "../../api/types";
import { useT } from "../../i18n";
import { useGame } from "../../store/game";
import { CONTENT_ICONS, Icon, type IconName } from "../ui/Icon";
import { Spinner, TabPanel, Tabs } from "../ui/primitives";

export type PanelId = "inventory" | "quests" | "map" | "journal" | "relations" | "memories" | "codex" | "achievements";

export const PANELS: { id: PanelId; icon: IconName }[] = [
  { id: "inventory", icon: "bag" },
  { id: "quests", icon: "scroll" },
  { id: "map", icon: "map" },
  { id: "journal", icon: "book" },
  { id: "relations", icon: "heart" },
  { id: "memories", icon: "brain" },
  { id: "codex", icon: "feather" },
  { id: "achievements", icon: "star" },
];

export function SidePanel({ initial = "inventory", compactTabs = true }: { initial?: PanelId; compactTabs?: boolean }) {
  const { t } = useT();
  const game = useGame((s) => s.game);
  const [tab, setTab] = useState<PanelId>(initial);
  if (!game) return null;
  const activeQuests = game.quests.filter((q) => q.status === "active").length;
  return (
    <div className="flex h-full min-h-0 flex-col">
      <Tabs
        label={t("a11y.sidePanel")}
        active={tab}
        onChange={(id) => setTab(id as PanelId)}
        compact={compactTabs}
        tabs={PANELS.map((p) => ({
          id: p.id,
          icon: p.icon,
          label: t(`panels.${p.id}`),
          badge: p.id === "quests" ? activeQuests : undefined,
        }))}
      />
      {compactTabs && <h2 className="mt-2 font-display text-lg font-semibold">{t(`panels.${tab}`)}</h2>}
      <div className="scroll-thin mt-2 min-h-0 flex-1 overflow-y-auto pr-1">
        <TabPanel id={tab}>
          {tab === "inventory" && <InventoryTab game={game} />}
          {tab === "quests" && <QuestsTab game={game} />}
          {tab === "map" && <MapTab game={game} />}
          {tab === "journal" && <JournalTab game={game} />}
          {tab === "relations" && <RelationsTab game={game} />}
          {tab === "memories" && <MemoriesTab game={game} />}
          {tab === "codex" && <CodexTab game={game} />}
          {tab === "achievements" && <AchievementsTab game={game} />}
        </TabPanel>
      </div>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="py-6 text-center text-sm text-muted">{text}</p>;
}

function InventoryTab({ game }: { game: GameView }) {
  const { t } = useT();
  const act = useGame((s) => s.act);
  const busy = useGame((s) => s.phase !== "idle" || Boolean(s.game?.ending || s.game?.defeated));
  const run = (verb: string, label: string, target: string) =>
    void act(label, { verb, target, item: null, interaction: null, label, kind: "item" });
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">{t("panels.capacity", game.capacity)}</p>
      {game.inventory.length === 0 ? (
        <Empty text={t("panels.emptyInventory")} />
      ) : (
        <ul className="space-y-2">
          {game.inventory.map((item) => (
            <li key={item.id} className="rounded-xl border border-rule bg-surface p-3">
              <p className="flex items-center gap-2 font-semibold">
                <Icon name={CONTENT_ICONS[item.icon] ?? "bag"} size={18} className="text-accent" />
                {item.name}
              </p>
              <p className="mt-1 text-sm text-muted">{item.description}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(
                  [
                    ["examine", t("panels.examine")],
                    ["use", t("panels.use")],
                    ["drop", t("panels.drop")],
                  ] as const
                ).map(([verb, label]) => (
                  <button
                    key={verb}
                    type="button"
                    disabled={busy}
                    onClick={() => run(verb, `${label} ${item.name}`, item.id)}
                    className="min-h-9 rounded-lg border border-rule px-3 text-sm hover:bg-surface-2 disabled:opacity-50"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function QuestsTab({ game }: { game: GameView }) {
  const { t } = useT();
  if (game.quests.length === 0) return <Empty text={t("panels.noQuests")} />;
  return (
    <ul className="space-y-3">
      {game.quests.map((q) => (
        <li
          key={q.id}
          className={`rounded-xl border p-3 ${q.status === "active" ? "border-accent bg-surface" : "border-rule bg-surface-2 opacity-90"}`}
        >
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted">
            <span>{t(`panels.questKind.${q.kind}`)}</span>·<span>{t(`panels.questStatus.${q.status}`)}</span>
          </div>
          <h4 className="mt-0.5 font-display text-base font-semibold">{q.name}</h4>
          <p className="text-sm text-muted">{q.outcome ?? q.description}</p>
          <ul className="mt-2 space-y-1">
            {q.objectives.map((o) => (
              <li key={o.id} className="flex items-start gap-2 text-sm">
                <span
                  aria-hidden
                  className={`mt-0.5 inline-flex size-4 shrink-0 items-center justify-center rounded border ${o.done ? "border-good bg-good text-white dark:text-black" : "border-rule"}`}
                >
                  {o.done ? "✓" : ""}
                </span>
                <span className={o.done ? "text-muted line-through" : ""}>
                  <span className="sr-only">{o.done ? "✓ " : "○ "}</span>
                  {o.text}
                  {o.optional && <span className="ml-1 text-xs text-muted">({t("panels.optional")})</span>}
                </span>
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}

function MapTab({ game }: { game: GameView }) {
  const { t } = useT();
  const known = game.map.regions.filter((r) => r.known);
  // A manual region choice lasts until the mug moves to another region.
  const [choice, setChoice] = useState<{ region: string; from: string } | null>(null);
  const region = choice && choice.from === game.location.region ? choice.region : game.location.region;
  const setRegion = (r: string) => setChoice({ region: r, from: game.location.region });
  const nodes = game.map.nodes.filter((n) => n.region === region);
  const ids = new Set(nodes.map((n) => n.id));
  const pos = new Map(nodes.map((n) => [n.id, n]));
  const edges = game.map.edges.filter(([a, b]) => ids.has(a) && ids.has(b));
  const outward = game.map.edges.filter(([a, b]) => ids.has(a) !== ids.has(b));
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1" role="group" aria-label={t("panels.map")}>
        {game.map.regions.map((r) => (
          <button
            key={r.id}
            type="button"
            disabled={!r.known}
            aria-pressed={region === r.id}
            onClick={() => setRegion(r.id)}
            className={`min-h-9 rounded-lg px-2.5 text-sm font-semibold ${region === r.id ? "bg-accent-soft" : "text-muted hover:bg-surface-2"} disabled:opacity-40`}
            title={r.known ? r.name : t("panels.unknownRegion")}
          >
            {r.known ? r.name : "???"}
          </button>
        ))}
      </div>
      {known.length > 0 && (
        <svg viewBox="-8 -8 116 116" className="card w-full" role="img" aria-label={t("panels.map")}>
          {edges.map(([a, b]) => {
            const pa = pos.get(a)!;
            const pb = pos.get(b)!;
            return (
              <line
                key={`${a}-${b}`}
                x1={pa.x * 100}
                y1={pa.y * 100}
                x2={pb.x * 100}
                y2={pb.y * 100}
                stroke="var(--c-rule)"
                strokeWidth="1.2"
                strokeDasharray={pa.visited && pb.visited ? undefined : "2 2"}
              />
            );
          })}
          {outward.map(([a, b]) => {
            const inside = pos.get(a) ?? pos.get(b);
            if (!inside) return null;
            return (
              <circle key={`o-${a}-${b}`} cx={inside.x * 100} cy={inside.y * 100} r="5.5" fill="none" stroke="var(--c-copper)" strokeWidth="0.8" strokeDasharray="1.5 1.5" />
            );
          })}
          {nodes.map((n) => (
            <g key={n.id}>
              {n.current && (
                <circle cx={n.x * 100} cy={n.y * 100} r="6" fill="none" stroke="var(--c-accent)" strokeWidth="1.2">
                  <animate attributeName="r" values="4;9;4" dur="2.4s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="1;0.2;1" dur="2.4s" repeatCount="indefinite" />
                </circle>
              )}
              <circle
                cx={n.x * 100}
                cy={n.y * 100}
                r={n.current ? 3.6 : 2.8}
                fill={n.current ? "var(--c-accent)" : n.visited ? "var(--c-coffee)" : "var(--c-surface-2)"}
                stroke="var(--c-ink)"
                strokeWidth="0.5"
              />
              <text
                x={n.x * 100}
                y={n.y * 100 + 8}
                textAnchor="middle"
                fontSize="4.2"
                fill="var(--c-ink)"
                fontWeight={n.current ? 700 : 400}
              >
                {n.name}
              </text>
            </g>
          ))}
        </svg>
      )}
      <ul className="sr-only">
        {nodes.map((n) => (
          <li key={n.id}>
            {n.name}: {n.current ? t("panels.current") : n.visited ? t("panels.visited") : t("panels.known")}
          </li>
        ))}
      </ul>
      <p className="flex flex-wrap gap-3 text-xs text-muted">
        <span>● {t("panels.current")}</span>
        <span>— {t("panels.visited")}</span>
        <span>- - {t("panels.known")}</span>
      </p>
    </div>
  );
}

function useRemote<T>(load: () => Promise<T>, deps: unknown[]): T | null {
  const [data, setData] = useState<T | null>(null);
  useEffect(() => {
    let alive = true;
    load()
      .then((d) => alive && setData(d))
      .catch(() => alive && setData(null));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return data;
}

function JournalTab({ game }: { game: GameView }) {
  const { t, lang } = useT();
  const entries = useRemote<JournalEntry[]>(() => api.journal(game.id, lang), [game.id, game.turn, lang]);
  if (!entries) return <Spinner label={t("a11y.loading")} />;
  if (entries.length === 0) return <Empty text={t("panels.journalEmpty")} />;
  return (
    <ol className="space-y-3">
      {entries.map((e) => (
        <li key={e.id} className="border-l-2 border-accent pl-3">
          <p className="text-xs text-muted">
            {t("panels.turn", { n: e.turn })} · {e.location}
          </p>
          <h4 className="font-display font-semibold">{e.title}</h4>
          <p className="text-sm">{e.body}</p>
          {e.participants.length > 0 && (
            <p className="mt-1 text-xs text-muted">
              {t("panels.with")}: {e.participants.join(", ")}
            </p>
          )}
          {e.decision && (
            <p className="mt-1 text-xs italic text-muted">
              {t("panels.decision")}: “{e.decision}”
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}

function RelationsTab({ game }: { game: GameView }) {
  const { t } = useT();
  if (game.relationships.length === 0) return <Empty text={t("panels.noRelations")} />;
  return (
    <ul className="space-y-2">
      {game.relationships.map((r) => {
        const pct = (r.value + 100) / 2;
        return (
          <li key={r.id} className="rounded-xl border border-rule bg-surface p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="flex items-center gap-2 font-semibold">
                <Icon name={CONTENT_ICONS[r.icon] ?? "users"} size={18} className="text-accent" />
                {r.name}
              </p>
              <span className="text-sm font-semibold">{r.label}</span>
            </div>
            <p className="text-xs text-muted">
              {r.kind} · {r.location}
              {r.companion && ` · ${t("panels.companion")}`}
            </p>
            <div
              className="relative mt-2 h-2 rounded-full bg-gradient-to-r from-bad via-surface-2 to-good"
              role="meter"
              aria-label={r.name}
              aria-valuemin={-100}
              aria-valuemax={100}
              aria-valuenow={r.value}
              aria-valuetext={`${r.value} — ${r.label}`}
            >
              <span
                aria-hidden
                className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface bg-ink"
                style={{ left: `${pct}%` }}
              />
            </div>
            {r.memories > 0 && <p className="mt-1.5 text-xs text-muted">{t("panels.remembers", { n: r.memories })}</p>}
          </li>
        );
      })}
    </ul>
  );
}

function MemoriesTab({ game }: { game: GameView }) {
  const { t, lang } = useT();
  const mem = useRemote<Memories>(() => api.memories(game.id, lang), [game.id, game.turn, lang]);
  if (!mem) return <Spinner label={t("a11y.loading")} />;
  if (!mem.summary && mem.facts.length === 0) return <Empty text={t("panels.noMemories")} />;
  return (
    <div className="space-y-4">
      {mem.summary && (
        <section>
          <h4 className="font-display font-semibold">{t("panels.summary")}</h4>
          <p className="text-sm">{mem.summary}</p>
        </section>
      )}
      <section>
        <h4 className="font-display font-semibold">{t("panels.facts")}</h4>
        <ul className="mt-1 space-y-2">
          {mem.facts.map((f) => (
            <li key={f.id} className="rounded-lg bg-surface-2 px-3 py-2 text-sm">
              <p>
                <span aria-hidden>{"★".repeat(Math.min(5, f.importance))} </span>
                {f.text}
              </p>
              {f.known_by.length > 0 && (
                <p className="mt-0.5 text-xs text-muted">{t("panels.knownBy", { names: f.known_by.join(", ") })}</p>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function CodexTab({ game }: { game: GameView }) {
  const { t } = useT();
  if (game.codex.length === 0) return <Empty text={t("panels.noCodex")} />;
  const kinds = ["npc", "location", "item", "feature"] as const;
  return (
    <div className="space-y-4">
      {kinds.map((kind) => {
        const entries = game.codex.filter((c) => c.kind === kind);
        if (!entries.length) return null;
        return (
          <section key={kind}>
            <h4 className="font-display font-semibold">{t(`panels.codexKinds.${kind}`)}</h4>
            <dl className="mt-1 space-y-2">
              {entries.map((c) => (
                <div key={c.id}>
                  <dt className="text-sm font-semibold">{c.name}</dt>
                  <dd className="text-sm text-muted">{c.description}</dd>
                </div>
              ))}
            </dl>
          </section>
        );
      })}
    </div>
  );
}

function AchievementsTab({ game }: { game: GameView }) {
  const { t } = useT();
  const unlocked = game.achievements.filter((a) => a.unlocked).length;
  return (
    <div className="space-y-2">
      <p className="text-sm text-muted">{t("panels.unlocked", { n: unlocked, total: game.achievements.length })}</p>
      <ul className="grid gap-2">
        {game.achievements.map((a) => (
          <li
            key={a.id}
            className={`flex items-start gap-3 rounded-xl border p-3 ${a.unlocked ? "border-accent bg-accent-soft" : "border-rule bg-surface opacity-75"}`}
          >
            <Icon name={a.unlocked ? "star" : "hourglass"} size={20} className={a.unlocked ? "text-accent" : "text-muted"} />
            <div>
              <p className="font-semibold">{a.name}</p>
              {a.description && <p className="text-sm text-muted">{a.description}</p>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
