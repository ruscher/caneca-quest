import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { Composer } from "../components/game/Composer";
import { NarrativeFeed } from "../components/game/NarrativeFeed";
import { PANELS, type PanelId, SidePanel } from "../components/game/SidePanel";
import { Abilities, LocationCard, MugCard, Vitals } from "../components/game/StatsPanel";
import { Icon } from "../components/ui/Icon";
import { Button, Dialog, IconButton } from "../components/ui/primitives";
import { useT } from "../i18n";
import { errorCode, useGame } from "../store/game";

export function GameScreen() {
  const { t } = useT();
  const game = useGame((s) => s.game);
  const go = useGame((s) => s.go);
  const closeGame = useGame((s) => s.closeGame);
  const openSettings = useGame((s) => s.openSettings);
  const toast = useGame((s) => s.toast);
  const [sheet, setSheet] = useState<null | "stats" | PanelId>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const lastChapter = useRef<number | null>(null);

  const saveNow = async () => {
    if (!game) return;
    const label = `${game.location.name} · ${game.clock}`;
    try {
      await api.createCheckpoint(game.id, label);
      toast("success", `raw:${t("game.savedNow", { label })}`);
    } catch (err) {
      toast("error", errorCode(err));
    }
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void saveNow();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  useEffect(() => {
    if (!game) return;
    if (lastChapter.current !== null && game.chapter.number > lastChapter.current) {
      setBanner(game.chapter.title);
      const id = setTimeout(() => setBanner(null), 3800);
      lastChapter.current = game.chapter.number;
      return () => clearTimeout(id);
    }
    lastChapter.current = game.chapter.number;
  }, [game]);

  if (!game) return null;
  const finished = Boolean(game.ending || game.defeated);

  return (
    <div className="flex h-dvh flex-col">
      <a href="#composer" className="sr-only-focusable absolute left-2 top-2 z-50 rounded bg-surface px-3 py-2">
        {t("a11y.skip")}
      </a>
      <header className="flex items-center gap-2 border-b border-rule bg-bg/80 px-2 py-1.5 backdrop-blur-md sm:px-4">
        <span aria-hidden className="text-2xl">☕</span>
        <div className="min-w-0 flex-1">
          <p className="truncate font-display text-[0.95rem] font-semibold leading-tight sm:text-lg">
            {game.chapter.title}
          </p>
          <p className="truncate text-xs text-muted">
            {game.location.name} · {game.region.name} · <span className="tabular-nums">{game.clock}</span>
          </p>
        </div>
        <IconButton icon="save" label={t("game.saveNow")} onClick={() => void saveNow()} className="hidden sm:inline-flex" />
        <IconButton icon="settings" label={t("welcome.settings")} onClick={() => openSettings(true)} />
        <IconButton icon="menu" label={t("game.menu")} onClick={() => setMenuOpen(true)} />
      </header>

      {/* compact vitals strip for tablet/mobile */}
      <button
        type="button"
        onClick={() => setSheet("stats")}
        className="flex min-h-11 items-center gap-3 border-b border-rule bg-surface/70 px-3 py-1.5 text-left lg:hidden"
        aria-label={t("a11y.stats")}
      >
        <MiniVital icon="flame" value={`${Math.round(game.stats.temperature)}°`} tone={game.stats.temperature < 40 ? "text-cold" : "text-hot"} />
        <MiniVital icon="cup" value={`${Math.round(game.stats.coffee)}%`} tone="text-coffee" />
        <MiniVital icon="shield" value={`${Math.round(game.stats.integrity)}%`} tone={game.stats.integrity <= 50 ? "text-bad" : "text-good"} />
        <MiniVital icon="bolt" value={`${Math.round(game.stats.energy)}%`} tone="text-warn" />
        <span className="ml-auto text-xs text-muted">{t("stats.level", { n: game.stats.level })}</span>
      </button>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)] md:grid-cols-[minmax(0,1fr)_20rem] lg:grid-cols-[17rem_minmax(0,1fr)_21rem] xl:grid-cols-[19rem_minmax(0,1fr)_23rem]">
        <aside
          aria-label={t("a11y.stats")}
          className="scroll-thin hidden min-h-0 space-y-5 overflow-y-auto border-r border-rule px-4 py-4 lg:block"
        >
          <MugCard game={game} />
          <Vitals game={game} />
          <LocationCard game={game} />
          <Abilities game={game} />
        </aside>

        <main className="flex min-h-0 min-w-0 flex-col" id="story">
          <NarrativeFeed />
          {finished && <EndingCard onRestore={() => go("saves")} onLeave={closeGame} />}
          <div id="composer">
            <Composer />
          </div>
        </main>

        <aside aria-label={t("a11y.sidePanel")} className="hidden min-h-0 border-l border-rule px-3 py-3 md:block">
          <SidePanel />
        </aside>
      </div>

      {/* mobile bottom navigation */}
      <nav aria-label={t("a11y.sidePanel")} className="grid grid-cols-5 border-t border-rule bg-bg/90 pb-[env(safe-area-inset-bottom)] md:hidden">
        {(["stats", "inventory", "quests", "map", "journal"] as const).map((id) => {
          const icon = id === "stats" ? "cup" : PANELS.find((p) => p.id === id)!.icon;
          const label = id === "stats" ? t("game.mugTab") : t(`panels.${id}`);
          return (
            <button
              key={id}
              type="button"
              onClick={() => setSheet(id)}
              className="flex min-h-14 flex-col items-center justify-center gap-0.5 text-[0.7rem] font-semibold text-muted hover:text-ink"
            >
              <Icon name={icon} size={20} />
              <span className="max-w-full truncate px-1">{label}</span>
            </button>
          );
        })}
      </nav>

      <Dialog
        open={sheet !== null}
        onClose={() => setSheet(null)}
        title={sheet === "stats" ? game.mug.name : t(`panels.${(sheet ?? "inventory") as PanelId}`)}
        closeLabel={t("a11y.close")}
      >
        {sheet === "stats" ? (
          <div className="space-y-5">
            <MugCard game={game} compact />
            <Vitals game={game} />
            <LocationCard game={game} />
            <Abilities game={game} />
          </div>
        ) : sheet ? (
          <div className="h-[min(70dvh,40rem)]">
            <SidePanel key={sheet} initial={sheet} compactTabs />
          </div>
        ) : null}
      </Dialog>

      <Dialog open={menuOpen} onClose={() => setMenuOpen(false)} title={t("game.menu")} closeLabel={t("a11y.close")}>
        <div className="grid gap-2">
          <Button icon="save" onClick={() => void saveNow().then(() => setMenuOpen(false))}>
            {t("game.saveNow")}
          </Button>
          <Button icon="book" onClick={() => { setMenuOpen(false); go("saves"); }}>
            {t("welcome.load")}
          </Button>
          <Button icon="help" onClick={() => { setMenuOpen(false); go("help"); }}>
            {t("welcome.help")}
          </Button>
          <Button icon="settings" onClick={() => { setMenuOpen(false); openSettings(true); }}>
            {t("welcome.settings")}
          </Button>
          <Button icon="door" variant="ghost" onClick={() => { setMenuOpen(false); closeGame(); }}>
            {t("game.leave")}
          </Button>
        </div>
      </Dialog>

      {banner && (
        <div
          role="status"
          className="pointer-events-none fixed inset-0 z-40 flex items-center justify-center bg-black/40 backdrop-blur-[1px]"
        >
          <div className="animate-rise card mx-4 px-8 py-6 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">{t("game.chapterReached")}</p>
            <p className="mt-1 font-display text-2xl font-semibold sm:text-3xl">{banner}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function MiniVital({ icon, value, tone }: { icon: "flame" | "cup" | "shield" | "bolt"; value: string; tone: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-sm font-semibold tabular-nums">
      <Icon name={icon} size={16} className={tone} />
      {value}
    </span>
  );
}

function EndingCard({ onRestore, onLeave }: { onRestore: () => void; onLeave: () => void }) {
  const { t } = useT();
  const game = useGame((s) => s.game);
  if (!game) return null;
  const title = game.ending ? `${t("game.endingTitle")}: ${game.ending.name}` : t("game.defeatTitle");
  return (
    <section aria-labelledby="ending-title" className="mx-auto mb-3 w-full max-w-[44rem] px-4">
      <div className="card animate-rise border-accent p-5 text-center">
        <Icon name={game.ending ? "star" : "shield"} size={28} className="mx-auto text-accent" />
        <h2 id="ending-title" className="mt-2 font-display text-2xl font-semibold">
          {title}
        </h2>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <Button icon="hourglass" onClick={onRestore}>
            {t("game.restore")}
          </Button>
          <Button variant="primary" icon="plus" onClick={onLeave}>
            {t("game.newAdventure")}
          </Button>
        </div>
      </div>
    </section>
  );
}

