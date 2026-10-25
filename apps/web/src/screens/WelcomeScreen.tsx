import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { AISettings, GameSummary } from "../api/types";
import { MugAvatar } from "../components/game/MugAvatar";
import { Button } from "../components/ui/primitives";
import { useT } from "../i18n";
import { errorCode, useGame } from "../store/game";
import { prefersReducedMotion, usePrefs } from "../store/prefs";

export function WelcomeScreen() {
  const { t } = useT();
  const go = useGame((s) => s.go);
  const openGame = useGame((s) => s.openGame);
  const openSettings = useGame((s) => s.openSettings);
  const toast = useGame((s) => s.toast);
  const lastGameId = usePrefs((s) => s.lastGameId);
  const motion = usePrefs((s) => s.motion);
  const [games, setGames] = useState<GameSummary[] | null>(null);
  const [ai, setAi] = useState<AISettings | null>(null);
  const [offline, setOffline] = useState(false);
  const [opening, setOpening] = useState(false);

  const fetchAll = useCallback(
    () =>
      Promise.all([api.listGames(), api.aiSettings()])
        .then(([g, a]) => {
          setGames(g);
          setAi(a);
          setOffline(false);
        })
        .catch(() => setOffline(true)),
    [],
  );
  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);
  const load = () => {
    setOffline(false);
    void fetchAll();
  };

  const last = games?.find((g) => g.id === lastGameId && g.status === "active") ?? games?.find((g) => g.status === "active");

  const resume = async (id: string) => {
    setOpening(true);
    try {
      await openGame(id);
    } catch (err) {
      toast("error", errorCode(err));
    } finally {
      setOpening(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col items-center justify-center px-5 py-10 text-center">
      <MugAvatar
        mug={{ color: "#f4efe6", style: "classic", drink: "black_coffee" }}
        size={150}
        label={t("app.title")}
        animated={!prefersReducedMotion(motion)}
      />
      <h1 className="mt-3 font-display text-5xl font-bold tracking-tight sm:text-6xl">{t("app.title")}</h1>
      <p className="mt-1 font-display text-xl text-accent italic sm:text-2xl">{t("app.subtitle")}</p>
      <p className="mx-auto mt-5 max-w-xl font-read text-lg text-muted">{t("app.tagline")}</p>

      {offline ? (
        <div role="alert" className="card mt-8 max-w-md p-5">
          <p className="font-semibold">{t("welcome.offline")}</p>
          <p className="mt-1 text-sm text-muted">{t("welcome.offlineHint")}</p>
          <Button className="mt-3" onClick={load} icon="play">
            {t("welcome.retry")}
          </Button>
        </div>
      ) : (
        <nav aria-label={t("a11y.menu")} className="mt-8 grid w-full max-w-sm gap-2.5">
          {last && (
            <Button variant="primary" icon="play" disabled={opening} onClick={() => void resume(last.id)} className="min-h-14 text-lg">
              <span className="flex flex-col items-start leading-tight">
                <span>{t("welcome.continue")}</span>
                <span className="text-xs font-normal opacity-85">
                  {t("welcome.continueDetail", { name: last.mug.name, chapter: `${last.location}` })}
                </span>
              </span>
            </Button>
          )}
          <Button variant={last ? "secondary" : "primary"} icon="plus" onClick={() => go("create")} className="min-h-12">
            {t("welcome.newGame")}
          </Button>
          <Button icon="book" onClick={() => go("saves")} disabled={!games?.length}>
            {t("welcome.load")}
          </Button>
          <div className="flex flex-wrap justify-center gap-1">
            <Button variant="ghost" icon="settings" onClick={() => openSettings(true)} className="px-2 text-sm">
              {t("welcome.settings")}
            </Button>
            <Button variant="ghost" icon="help" onClick={() => go("help")} className="px-2 text-sm">
              {t("welcome.help")}
            </Button>
            <Button variant="ghost" icon="heart" onClick={() => go("credits")} className="px-2 text-sm">
              {t("welcome.credits")}
            </Button>
          </div>
          {ai && (
            <p className="mt-2 text-sm text-muted">
              {ai.provider === "offline"
                ? t("welcome.aiOff")
                : t("welcome.aiOn", { provider: `${ai.provider}${ai.models[ai.provider] ? ` · ${ai.models[ai.provider]}` : ""}` })}
            </p>
          )}
        </nav>
      )}
    </main>
  );
}
