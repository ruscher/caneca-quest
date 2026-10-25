import type { GameView } from "../../api/types";
import { useT } from "../../i18n";
import { useGame } from "../../store/game";
import { prefersReducedMotion, usePrefs } from "../../store/prefs";
import { CONTENT_ICONS, Icon } from "../ui/Icon";
import { Meter } from "../ui/primitives";
import { MugAvatar } from "./MugAvatar";

export function MugCard({ game, compact = false }: { game: GameView; compact?: boolean }) {
  const { t } = useT();
  const motion = usePrefs((s) => s.motion);
  const s = game.stats;
  const span = Math.max(1, s.xp_next - s.xp_level_start);
  const xpPct = Math.min(100, ((s.xp - s.xp_level_start) / span) * 100);
  return (
    <div className={`flex items-center gap-3 ${compact ? "" : "flex-col text-center"}`}>
      <MugAvatar
        mug={game.mug}
        size={compact ? 64 : 132}
        label={t("a11y.mugPortrait", { name: game.mug.name })}
        animated={!prefersReducedMotion(motion)}
        state={{
          temperature: s.temperature,
          integrity: s.integrity,
          energy: s.energy,
          hidden: game.statuses.some((x) => x.id === "hidden"),
        }}
      />
      <div className={compact ? "min-w-0" : "w-full"}>
        <p className="truncate font-display text-xl font-semibold">{game.mug.name}</p>
        <p className="text-sm text-muted">{t("stats.level", { n: s.level })}</p>
        <div
          className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-2"
          role="progressbar"
          aria-label="XP"
          aria-valuemin={s.xp_level_start}
          aria-valuemax={s.xp_next}
          aria-valuenow={s.xp}
          aria-valuetext={t("stats.xp", { xp: s.xp, next: s.xp_next })}
        >
          <div className="h-full rounded-full bg-accent transition-[width] duration-700" style={{ width: `${xpPct}%` }} />
        </div>
        <p className="mt-0.5 text-xs tabular-nums text-muted">{t("stats.xp", { xp: s.xp, next: s.xp_next })}</p>
      </div>
    </div>
  );
}

export function Vitals({ game }: { game: GameView }) {
  const { t } = useT();
  const s = game.stats;
  const tempTone = s.temperature >= 60 ? "text-hot" : s.temperature < 40 ? "text-cold" : "text-copper";
  const status = (id: string) => game.statuses.find((x) => x.id === id)?.label;
  return (
    <div className="space-y-3">
      <Meter
        label={t("stats.temperature")}
        value={s.temperature}
        unit="°C"
        icon="flame"
        tone={tempTone}
        hint={status("hot") ?? status("lukewarm") ?? status("cold") ?? status("overheated")}
      />
      <Meter label={t("stats.coffee")} value={s.coffee} icon="cup" tone="text-coffee" hint={status("buoyant") ?? status("empty")} />
      <Meter
        label={t("stats.integrity")}
        value={s.integrity}
        icon="shield"
        tone={s.integrity <= 50 ? "text-bad" : "text-good"}
        hint={status("cracked") ?? status("shattered")}
      />
      <Meter label={t("stats.energy")} value={s.energy} icon="bolt" tone="text-warn" hint={status("tired")} />
      <div className="grid grid-cols-2 gap-2 pt-1 text-sm">
        <div className="rounded-xl bg-surface-2 px-3 py-2">
          <p className="text-muted">{t("stats.courage")}</p>
          <p className="font-display text-lg font-semibold tabular-nums">{s.courage}</p>
        </div>
        <div className="rounded-xl bg-surface-2 px-3 py-2">
          <p className="text-muted">{t("stats.creativity")}</p>
          <p className="font-display text-lg font-semibold tabular-nums">{s.creativity}</p>
        </div>
      </div>
      {game.statuses.length > 0 && (
        <div>
          <h3 className="sr-only">{t("stats.statuses")}</h3>
          <ul className="flex flex-wrap gap-1.5">
            {game.statuses.map((st) => (
              <li key={st.id} className="rounded-full border border-rule px-2 py-0.5 text-xs font-semibold text-muted">
                {st.label}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function Abilities({ game }: { game: GameView }) {
  const { t } = useT();
  const act = useGame((s) => s.act);
  const busy = useGame((s) => s.phase !== "idle");
  return (
    <section>
      <h3 className="mb-2 font-display text-base font-semibold">{t("stats.abilities")}</h3>
      {game.abilities.length === 0 ? (
        <p className="text-sm text-muted">{t("stats.noAbilities")}</p>
      ) : (
        <ul className="space-y-2">
          {game.abilities.map((ab) => (
            <li key={ab.id} className="rounded-xl border border-rule bg-surface px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <p className="font-semibold leading-tight">{ab.name}</p>
                {ab.kind === "active" ? (
                  <button
                    type="button"
                    disabled={busy || ab.cooldown > 0}
                    onClick={() =>
                      void act(`${t("stats.use")} ${ab.name}`, {
                        verb: "ability",
                        target: ab.id,
                        item: null,
                        interaction: null,
                        label: ab.name,
                        kind: "action",
                      })
                    }
                    className="min-h-9 rounded-lg bg-accent-soft px-3 text-sm font-semibold hover:brightness-105 disabled:opacity-50"
                  >
                    {ab.cooldown > 0 ? t("stats.cooldown", { n: ab.cooldown }) : t("stats.use")}
                  </button>
                ) : (
                  <span className="text-xs text-muted">{t("stats.passive")}</span>
                )}
              </div>
              <p className="mt-0.5 text-sm text-muted">{ab.description}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function LocationCard({ game }: { game: GameView }) {
  const { t } = useT();
  const act = useGame((s) => s.act);
  const busy = useGame((s) => s.phase !== "idle");
  const loc = game.location;
  return (
    <section aria-labelledby="loc-title" className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted">{t("stats.location")}</p>
      <h3 id="loc-title" className="font-display text-lg font-semibold leading-tight">
        {loc.name}
      </h3>
      <p className="text-sm text-muted">{loc.short}</p>
      {loc.npcs.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {loc.npcs.map((n) => (
            <li key={n.id} className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-2 py-0.5 text-sm">
              <Icon name={CONTENT_ICONS[n.icon] ?? "users"} size={14} />
              {n.name}
              {n.remote && <span className="text-xs text-muted">({t("stats.remote")})</span>}
            </li>
          ))}
        </ul>
      )}
      {loc.exits.length > 0 && (
        <div>
          <p className="mb-1 mt-2 text-xs font-semibold uppercase tracking-wider text-muted">{t("stats.exits")}</p>
          <ul className="space-y-1">
            {loc.exits.map((ex) => (
              <li key={ex.to}>
                <button
                  type="button"
                  disabled={busy || Boolean(game.ending || game.defeated)}
                  onClick={() =>
                    void act(ex.label, {
                      verb: "go",
                      target: `exit:${ex.to}`,
                      item: null,
                      interaction: null,
                      label: ex.label,
                      kind: "move",
                    })
                  }
                  className="flex min-h-10 w-full items-center gap-2 rounded-lg px-2 py-1 text-left text-sm hover:bg-surface-2 disabled:opacity-50"
                >
                  <Icon name={ex.allowed ? "compass" : "key"} size={16} className={ex.allowed ? "text-accent" : "text-muted"} />
                  <span className={ex.visited ? "" : "font-semibold"}>{ex.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
