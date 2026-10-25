import { type FormEvent, useId, useState } from "react";
import type { AdventureSettings, Drink, Material, Mug, Personality, Style, Trait } from "../api/types";
import { MugAvatar } from "../components/game/MugAvatar";
import { Button, ChoiceGroup, Field, inputClass } from "../components/ui/primitives";
import { type Lang, LANGS, optionText, useT } from "../i18n";
import { errorCode, useGame } from "../store/game";
import { prefersReducedMotion, usePrefs } from "../store/prefs";

const COLORS = ["#f4efe6", "#2f2a28", "#b4472f", "#2f5d8a", "#3f7a5a", "#d9a441", "#8a4f7d", "#c97b84"];
const COLOR_NAMES: Record<string, [string, string]> = {
  "#f4efe6": ["Branca", "White"],
  "#2f2a28": ["Preta", "Black"],
  "#b4472f": ["Terracota", "Terracotta"],
  "#2f5d8a": ["Azul", "Blue"],
  "#3f7a5a": ["Verde", "Green"],
  "#d9a441": ["Amarela", "Yellow"],
  "#8a4f7d": ["Ameixa", "Plum"],
  "#c97b84": ["Rosa", "Pink"],
};
const STYLES: Style[] = ["classic", "striped", "dotted", "floral", "minimal", "rustic"];
const MATERIALS: Material[] = ["porcelain", "stoneware", "enamel", "glass"];
const DRINKS: Drink[] = ["black_coffee", "latte", "cappuccino", "hot_chocolate", "tea"];
const PERSONALITIES: Personality[] = ["optimistic", "sarcastic", "shy", "philosophical", "fearless"];
const TRAITS: Trait[] = ["brave", "creative", "sturdy", "thermal", "curious", "charming"];
const TONES: AdventureSettings["tone"][] = ["balanced", "fantasy", "mystery", "humor", "drama", "relaxing", "survival"];
const DIFFICULTIES: AdventureSettings["difficulty"][] = ["story", "adventure", "survival"];
const LENGTHS: AdventureSettings["narrative_length"][] = ["short", "normal", "detailed", "cinematic"];

const STEPS = ["identity", "look", "soul", "adventure"] as const;

export function CreateScreen() {
  const { t, lang, d } = useT();
  const go = useGame((s) => s.go);
  const startGame = useGame((s) => s.startGame);
  const toast = useGame((s) => s.toast);
  const setPrefs = usePrefs((s) => s.set);
  const motion = usePrefs((s) => s.motion);
  const nameId = useId();
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [mug, setMug] = useState<Mug>({
    name: "",
    color: COLORS[0]!,
    style: "classic",
    material: "porcelain",
    drink: "black_coffee",
    personality: "optimistic",
    traits: [],
  });
  const [settings, setSettings] = useState<AdventureSettings>({
    tone: "balanced",
    difficulty: "adventure",
    narrative_length: "normal",
    language: lang,
  });

  const opts = <T extends string>(group: Parameters<typeof optionText>[1], values: T[]) =>
    values.map((value) => ({ value, ...optionText(lang, group, value) }));

  const next = () => {
    if (step === 0 && !mug.name.trim()) {
      setError(t("create.errorName"));
      document.getElementById(nameId)?.focus();
      return;
    }
    setError(null);
    setStep((s) => Math.min(STEPS.length - 1, s + 1));
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (step < STEPS.length - 1) {
      next();
      return;
    }
    if (!mug.name.trim()) {
      setStep(0);
      setError(t("create.errorName"));
      return;
    }
    setBusy(true);
    try {
      if (settings.language !== lang) setPrefs({ language: settings.language });
      await startGame({ name: mug.name.trim(), mug: { ...mug, name: mug.name.trim() }, settings });
    } catch (err) {
      toast("error", errorCode(err));
    } finally {
      setBusy(false);
    }
  };

  const randomName = () => {
    const pool = d.create.nameSuggestions;
    setMug({ ...mug, name: pool[Math.floor(Math.random() * pool.length)] ?? "Aurora" });
    setError(null);
  };

  const stepKey = STEPS[step]!;

  return (
    <main className="mx-auto grid min-h-dvh max-w-5xl gap-6 px-4 py-6 md:grid-cols-[1fr_17rem] md:py-10">
      <form onSubmit={submit} className="card order-2 p-5 sm:p-7 md:order-1" noValidate>
        <p className="text-sm text-muted">{t("create.stepOf", { n: step + 1, total: STEPS.length })}</p>
        <h1 className="font-display text-3xl font-semibold">{t("create.title")}</h1>
        <ol className="mt-3 flex gap-1.5" aria-label={t("create.title")}>
          {STEPS.map((s, i) => (
            <li key={s} className="flex-1">
              <button
                type="button"
                onClick={() => (i <= step || mug.name.trim() ? setStep(i) : undefined)}
                aria-current={i === step ? "step" : undefined}
                className={`w-full rounded-full border-b-4 pb-1 text-left text-xs font-semibold sm:text-sm ${i <= step ? "border-accent text-ink" : "border-rule text-muted"}`}
              >
                {t(`create.steps.${s}`)}
              </button>
            </li>
          ))}
        </ol>

        <div className="mt-6 space-y-6" key={stepKey}>
          {stepKey === "identity" && (
            <>
              <Field id={nameId} label={t("create.name")} help={t("create.nameHelp")} error={error}>
                <div className="flex gap-2">
                  <input
                    id={nameId}
                    className={inputClass}
                    value={mug.name}
                    maxLength={40}
                    autoComplete="off"
                    placeholder={t("create.namePlaceholder")}
                    aria-invalid={Boolean(error)}
                    aria-describedby={error ? `${nameId}-error` : `${nameId}-help`}
                    onChange={(e) => {
                      setMug({ ...mug, name: e.target.value });
                      setError(null);
                    }}
                  />
                  <Button onClick={randomName} icon="sparkle" className="shrink-0" aria-label={t("create.randomName")}>
                    <span aria-hidden className="hidden sm:inline">
                      {t("create.randomName")}
                    </span>
                  </Button>
                </div>
              </Field>
              <ChoiceGroup
                legend={t("create.personality")}
                options={opts("personality", PERSONALITIES)}
                value={mug.personality}
                onChange={(v) => setMug({ ...mug, personality: v })}
              />
            </>
          )}

          {stepKey === "look" && (
            <>
              <ChoiceGroup
                legend={t("create.color")}
                columns={4}
                options={COLORS.map((c) => ({ value: c, label: COLOR_NAMES[c]![lang === "pt-BR" ? 0 : 1], swatch: c }))}
                value={mug.color}
                onChange={(v) => setMug({ ...mug, color: v })}
              />
              <ChoiceGroup
                legend={t("create.style")}
                columns={3}
                options={opts("style", STYLES)}
                value={mug.style}
                onChange={(v) => setMug({ ...mug, style: v })}
              />
              <ChoiceGroup
                legend={t("create.material")}
                options={opts("material", MATERIALS)}
                value={mug.material}
                onChange={(v) => setMug({ ...mug, material: v })}
              />
            </>
          )}

          {stepKey === "soul" && (
            <>
              <ChoiceGroup
                legend={t("create.drink")}
                options={opts("drink", DRINKS)}
                value={mug.drink}
                onChange={(v) => setMug({ ...mug, drink: v })}
              />
              <ChoiceGroup
                legend={t("create.traits")}
                multiple
                max={2}
                values={mug.traits}
                options={opts("trait", TRAITS)}
                onChange={(v) =>
                  setMug({
                    ...mug,
                    traits: mug.traits.includes(v) ? mug.traits.filter((x) => x !== v) : [...mug.traits, v].slice(0, 2),
                  })
                }
              />
            </>
          )}

          {stepKey === "adventure" && (
            <>
              <ChoiceGroup
                legend={t("create.tone")}
                options={opts("tone", TONES)}
                value={settings.tone}
                onChange={(v) => setSettings({ ...settings, tone: v })}
              />
              <ChoiceGroup
                legend={t("create.difficulty")}
                columns={3}
                options={opts("difficulty", DIFFICULTIES)}
                value={settings.difficulty}
                onChange={(v) => setSettings({ ...settings, difficulty: v })}
              />
              <ChoiceGroup
                legend={t("create.length")}
                options={opts("narrative_length", LENGTHS)}
                value={settings.narrative_length}
                onChange={(v) => setSettings({ ...settings, narrative_length: v })}
              />
              <ChoiceGroup
                legend={t("create.language")}
                options={LANGS.map((l) => ({ value: l, label: optionText(lang, "language", l).label }))}
                value={settings.language}
                onChange={(v) => setSettings({ ...settings, language: v as Lang })}
              />
            </>
          )}
        </div>

        <div className="mt-8 flex flex-wrap justify-between gap-2">
          <Button icon="chevronLeft" onClick={() => (step === 0 ? go("welcome") : setStep(step - 1))}>
            {t("create.back")}
          </Button>
          {/* Distinct keys: React must not morph the "next" button into the submit button
              while its click is still being handled (that would submit the form early). */}
          {step < STEPS.length - 1 ? (
            <Button key="next" variant="primary" onClick={next}>
              {t("create.next")}
            </Button>
          ) : (
            <Button key="start" variant="primary" type="submit" icon="sparkle" disabled={busy}>
              {t("create.start")}
            </Button>
          )}
        </div>
      </form>

      <aside className="order-1 md:order-2" aria-label={t("create.preview")}>
        <div className="card sticky top-6 flex flex-col items-center p-5 text-center">
          <MugAvatar
            mug={mug}
            size={170}
            label={t("a11y.mugPortrait", { name: mug.name || "…" })}
            animated={!prefersReducedMotion(motion)}
          />
          <p className="mt-2 font-display text-2xl font-semibold">{mug.name || "…"}</p>
          <p className="text-sm text-muted">
            {optionText(lang, "material", mug.material).label} · {optionText(lang, "style", mug.style).label}
          </p>
          <p className="text-sm text-muted">
            {optionText(lang, "drink", mug.drink).label} · {optionText(lang, "personality", mug.personality).label}
          </p>
          {mug.traits.length > 0 && (
            <p className="mt-1 text-sm">{mug.traits.map((tr) => optionText(lang, "trait", tr).label).join(" · ")}</p>
          )}
        </div>
      </aside>
    </main>
  );
}
