import { Button } from "../components/ui/primitives";
import { useT } from "../i18n";
import { useGame } from "../store/game";

function BackButton() {
  const { t } = useT();
  const go = useGame((s) => s.go);
  const game = useGame((s) => s.game);
  return (
    <Button icon="chevronLeft" onClick={() => go(game ? "game" : "welcome")}>
      {t("create.back")}
    </Button>
  );
}

export function HelpScreen() {
  const { t, d } = useT();
  return (
    <main className="mx-auto max-w-3xl px-5 py-8">
      <div className="flex items-center justify-between gap-3">
        <h1 className="font-display text-3xl font-semibold">{t("help.title")}</h1>
        <BackButton />
      </div>
      <div className="card mt-6 space-y-6 p-6">
        <p className="font-read text-lg">{t("help.intro")}</p>
        <section>
          <h2 className="font-display text-xl font-semibold">{t("help.examplesTitle")}</h2>
          <ul className="mt-2 flex flex-wrap gap-2">
            {d.help.examples.map((ex) => (
              <li key={ex} className="rounded-full border border-rule bg-surface-2 px-3 py-1 font-read text-sm italic">
                {ex}
              </li>
            ))}
          </ul>
        </section>
        <section>
          <h2 className="font-display text-xl font-semibold">{t("help.statsTitle")}</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {d.help.stats.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </section>
        <section>
          <h2 className="font-display text-xl font-semibold">{t("help.rulesTitle")}</h2>
          <p className="mt-1">{t("help.rules")}</p>
        </section>
        <section>
          <h2 className="font-display text-xl font-semibold">{t("help.aiTitle")}</h2>
          <p className="mt-1">{t("help.ai")}</p>
        </section>
        <section>
          <h2 className="font-display text-xl font-semibold">{t("help.shortcutsTitle")}</h2>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
            {d.help.shortcuts.map(([k, v]) => (
              <div key={k} className="contents">
                <dt>
                  <kbd className="rounded-md border border-rule bg-surface-2 px-2 py-0.5 font-ui text-sm">{k}</kbd>
                </dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </main>
  );
}

export function CreditsScreen() {
  const { t } = useT();
  return (
    <main className="mx-auto max-w-2xl px-5 py-8">
      <div className="flex items-center justify-between gap-3">
        <h1 className="font-display text-3xl font-semibold">{t("credits.title")}</h1>
        <BackButton />
      </div>
      <div className="card mt-6 space-y-3 p-6 font-read text-lg">
        <p>{t("credits.body")}</p>
        <p>{t("credits.tech")}</p>
        <p>{t("credits.fonts")}</p>
        <p>{t("credits.license")}</p>
      </div>
    </main>
  );
}
