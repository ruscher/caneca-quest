import { useCallback, useEffect, useId, useState } from "react";
import { api } from "../api/client";
import type { AISettings, AIStatus, AIUsage, ProviderId } from "../api/types";
import { Button, ChoiceGroup, Dialog, Field, inputClass, Spinner, TabPanel, Tabs, Toggle } from "../components/ui/primitives";
import { LANGS, optionText, useT } from "../i18n";
import { errorCode, useGame } from "../store/game";
import { usePrefs } from "../store/prefs";
import { narrator } from "../speech/narrator";

type Tab = "ai" | "visual" | "audio" | "language";

export function SettingsDialog() {
  const { t } = useT();
  const open = useGame((s) => s.settingsOpen);
  const openSettings = useGame((s) => s.openSettings);
  const [tab, setTab] = useState<Tab>("ai");
  return (
    <Dialog open={open} onClose={() => openSettings(false)} title={t("settings.title")} wide closeLabel={t("a11y.close")}>
      <Tabs
        label={t("settings.title")}
        active={tab}
        onChange={(id) => setTab(id as Tab)}
        tabs={[
          { id: "ai", label: t("settings.tabs.ai"), icon: "brain" },
          { id: "visual", label: t("settings.tabs.visual"), icon: "sun" },
          { id: "audio", label: t("settings.tabs.audio"), icon: "volume" },
          { id: "language", label: t("settings.tabs.language"), icon: "feather" },
        ]}
      />
      <div className="mt-4">
        <TabPanel id={tab}>
          {tab === "ai" && <AiSettings />}
          {tab === "visual" && <VisualSettings />}
          {tab === "audio" && <AudioSettings />}
          {tab === "language" && <LanguageSettings />}
        </TabPanel>
      </div>
    </Dialog>
  );
}

const PROVIDERS: ProviderId[] = ["offline", "ollama", "openai", "anthropic"];

function AiSettings() {
  const { t, d } = useT();
  const toast = useGame((s) => s.toast);
  const [ai, setAi] = useState<AISettings | null>(null);
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [checking, setChecking] = useState(false);
  const [test, setTest] = useState<string | null>(null);
  const [key, setKey] = useState("");
  const [usage, setUsage] = useState<AIUsage[]>([]);
  const ids = { url: useId(), model: useId(), key: useId(), temp: useId(), ctx: useId(), timeout: useId(), mem: useId() };

  useEffect(() => {
    api.aiSettings().then(setAi).catch((e) => toast("error", errorCode(e)));
    api.aiUsage().then(setUsage).catch(() => setUsage([]));
  }, [toast]);

  const provider = ai?.provider ?? "offline";
  const check = useCallback(
    async (p: ProviderId) => {
      if (p === "offline") return;
      setChecking(true);
      setStatus(null);
      try {
        setStatus(await api.aiStatus(p));
      } catch (e) {
        toast("error", errorCode(e));
      } finally {
        setChecking(false);
      }
    },
    [toast],
  );

  useEffect(() => {
    if (provider === "offline") return;
    let alive = true;
    api
      .aiStatus(provider)
      .then((st) => alive && setStatus(st))
      .catch((e) => alive && toast("error", errorCode(e)));
    return () => {
      alive = false;
    };
  }, [provider, toast]);

  if (!ai) return <Spinner label={t("a11y.loading")} />;
  const model = provider === "offline" ? "" : (ai.models[provider] ?? "");
  const external = provider === "openai" || provider === "anthropic";

  const save = async (next: AISettings = ai) => {
    try {
      setAi(await api.saveAiSettings(next));
      toast("success", `raw:${t("settings.saved")}`);
    } catch (e) {
      toast("error", errorCode(e));
    }
  };

  const setModel = (m: string) => {
    if (provider === "offline") return;
    setAi({ ...ai, models: { ...ai.models, [provider]: m } });
  };

  return (
    <div className="space-y-5">
      <ChoiceGroup
        legend={t("settings.ai.provider")}
        options={PROVIDERS.map((p) => ({
          value: p,
          label: d.settings.ai.providers[p][0] ?? p,
          description: d.settings.ai.providers[p][1] ?? "",
        }))}
        value={provider}
        onChange={(p) => setAi({ ...ai, provider: p })}
      />

      {provider === "ollama" && (
        <Field id={ids.url} label={t("settings.ai.url")}>
          <div className="flex gap-2">
            <input id={ids.url} className={inputClass} value={ai.ollama_url} onChange={(e) => setAi({ ...ai, ollama_url: e.target.value })} />
            <Button
              onClick={() => void api.saveAiSettings(ai).then((s) => { setAi(s); void check("ollama"); }).catch((e) => toast("error", errorCode(e)))}
            >
              {t("settings.ai.refresh")}
            </Button>
          </div>
        </Field>
      )}
      {provider === "openai" && (
        <Field id={ids.url} label={t("settings.ai.baseUrl")}>
          <input id={ids.url} className={inputClass} value={ai.openai_base_url} onChange={(e) => setAi({ ...ai, openai_base_url: e.target.value })} />
        </Field>
      )}

      {external && (
        <div className="space-y-3 rounded-xl border border-warn p-3">
          <p className="text-sm font-semibold text-warn">{t("settings.ai.externalWarning")}</p>
          <Toggle label={t("settings.ai.consent")} checked={ai.cloud_consent} onChange={(v) => setAi({ ...ai, cloud_consent: v })} />
          <Field
            id={ids.key}
            label={t("settings.ai.apiKey")}
            help={
              ai.keys?.[provider] === "env"
                ? t("settings.ai.keyEnv")
                : ai.keys?.[provider] === "file"
                  ? t("settings.ai.keySaved")
                  : t("settings.ai.keyMissing")
            }
          >
            <div className="flex flex-wrap gap-2">
              <input
                id={ids.key}
                type="password"
                autoComplete="off"
                className={`${inputClass} min-w-48 flex-1`}
                value={key}
                placeholder={t("settings.ai.keyPlaceholder")}
                onChange={(e) => setKey(e.target.value)}
              />
              <Button
                disabled={key.length < 8}
                onClick={() =>
                  void api
                    .setKey(provider, key)
                    .then(() => api.aiSettings())
                    .then((s) => {
                      setAi({ ...s, provider, models: ai.models, cloud_consent: ai.cloud_consent });
                      setKey("");
                      void check(provider);
                    })
                    .catch((e) => toast("error", errorCode(e)))
                }
              >
                {t("settings.ai.saveKey")}
              </Button>
              {ai.keys?.[provider] === "file" && (
                <Button
                  variant="ghost"
                  onClick={() => void api.deleteKey(provider).then(() => api.aiSettings()).then(setAi).catch(() => undefined)}
                >
                  {t("settings.ai.removeKey")}
                </Button>
              )}
            </div>
          </Field>
        </div>
      )}

      {provider !== "offline" && (
        <section className="space-y-3 rounded-xl bg-surface-2 p-3" aria-live="polite">
          <p className="text-sm">
            <span className="font-semibold">{t("settings.ai.status")}: </span>
            {checking || (status !== null && status.provider !== provider) ? (
              <Spinner label={t("a11y.loading")} />
            ) : status ? (
              status.available ? (
                <span className="text-good">{t("settings.ai.available", { detail: status.detail })}</span>
              ) : (
                <span className="text-bad">{t("settings.ai.unavailable", { detail: status.detail })}</span>
              )
            ) : null}
          </p>
          <Field id={ids.model} label={t("settings.ai.model")} help={status?.available && !status.models.length ? t("settings.ai.noModels") : undefined}>
            {status?.models.length ? (
              <select id={ids.model} className={inputClass} value={model} onChange={(e) => setModel(e.target.value)}>
                <option value="">{t("settings.ai.chooseModel")}</option>
                {status.models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                    {m.parameter_size ? ` · ${m.parameter_size}` : ""}
                  </option>
                ))}
              </select>
            ) : (
              <input id={ids.model} className={inputClass} value={model} onChange={(e) => setModel(e.target.value)} />
            )}
          </Field>
          {model && status && !status.models.some((m) => m.id === model) && status.models.length > 0 && (
            <p className="text-sm text-warn">{t("settings.ai.modelMissing")}</p>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              disabled={!model}
              onClick={() => {
                setTest("…");
                void api
                  .aiTest(provider, model)
                  .then((r) =>
                    setTest(
                      r.ok
                        ? t("settings.ai.testOk", { ms: r.latency_ms ?? 0, sample: r.sample ?? "" })
                        : t("settings.ai.testFail", { detail: r.detail ?? r.code ?? "" }),
                    ),
                  )
                  .catch((e) => setTest(t("settings.ai.testFail", { detail: errorCode(e) })));
              }}
            >
              {t("settings.ai.test")}
            </Button>
            {test && <p className="text-sm">{test}</p>}
          </div>
        </section>
      )}

      {provider !== "offline" && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id={ids.temp} label={`${t("settings.ai.temperature")}: ${ai.temperature.toFixed(1)}`}>
            <input id={ids.temp} type="range" min={0} max={1.5} step={0.1} value={ai.temperature} className="w-full accent-[var(--c-accent)]" onChange={(e) => setAi({ ...ai, temperature: Number(e.target.value) })} />
          </Field>
          <Field id={ids.ctx} label={t("settings.ai.context")}>
            <select id={ids.ctx} className={inputClass} value={ai.context_tokens} onChange={(e) => setAi({ ...ai, context_tokens: Number(e.target.value) })}>
              {[2048, 4096, 8192, 16384, 32768].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </Field>
          <Field id={ids.timeout} label={t("settings.ai.timeout")}>
            <input id={ids.timeout} type="number" min={10} max={600} className={inputClass} value={ai.timeout_seconds} onChange={(e) => setAi({ ...ai, timeout_seconds: Number(e.target.value) })} />
          </Field>
          <Field id={ids.mem} label={t("settings.ai.memoryTurns")}>
            <input id={ids.mem} type="number" min={0} max={12} className={inputClass} value={ai.memory_turns} onChange={(e) => setAi({ ...ai, memory_turns: Number(e.target.value) })} />
          </Field>
          <div className="sm:col-span-2">
            <Toggle label={t("settings.ai.aiIntent")} checked={ai.ai_intent} onChange={(v) => setAi({ ...ai, ai_intent: v })} />
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <Button variant="primary" icon="save" onClick={() => void save()}>
          {t("settings.save")}
        </Button>
      </div>

      <section>
        <h3 className="font-display font-semibold">{t("settings.ai.usage")}</h3>
        {usage.length === 0 ? (
          <p className="text-sm text-muted">{t("settings.ai.noUsage")}</p>
        ) : (
          <ul className="text-sm">
            {usage.map((u) => (
              <li key={`${u.provider}-${u.model}`}>
                {t("settings.ai.usageRow", { provider: u.provider, model: u.model ?? "?", turns: u.turns, tin: u.tokens_in, tout: u.tokens_out })}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function VisualSettings() {
  const { t, d } = useT();
  const prefs = usePrefs();
  const scaleId = useId();
  return (
    <div className="space-y-5">
      <ChoiceGroup
        legend={t("settings.theme")}
        columns={3}
        options={(["auto", "light", "dark"] as const).map((v) => ({ value: v, label: d.settings.themes[v] }))}
        value={prefs.theme}
        onChange={(v) => prefs.set({ theme: v })}
      />
      <Field id={scaleId} label={`${t("settings.fontScale")}: ${Math.round(prefs.fontScale * 100)}%`}>
        <input
          id={scaleId}
          type="range"
          min={0.85}
          max={1.5}
          step={0.05}
          value={prefs.fontScale}
          onChange={(e) => prefs.set({ fontScale: Number(e.target.value) })}
          className="w-full accent-[var(--c-accent)]"
        />
      </Field>
      <ChoiceGroup
        legend={t("settings.readingFont")}
        columns={3}
        options={(["literata", "atkinson", "sans"] as const).map((v) => ({ value: v, label: d.settings.fonts[v] }))}
        value={prefs.readingFont}
        onChange={(v) => prefs.set({ readingFont: v })}
      />
      <ChoiceGroup
        legend={t("settings.motion")}
        columns={3}
        options={(["auto", "full", "reduced"] as const).map((v) => ({ value: v, label: d.settings.motions[v] }))}
        value={prefs.motion}
        onChange={(v) => prefs.set({ motion: v })}
      />
      <ChoiceGroup
        legend={t("settings.textSpeed")}
        options={(["instant", "fast", "normal", "slow"] as const).map((v) => ({ value: v, label: d.settings.speeds[v] }))}
        value={prefs.textSpeed}
        onChange={(v) => prefs.set({ textSpeed: v })}
      />
      <Toggle label={t("settings.showChecks")} checked={prefs.showChecks} onChange={(v) => prefs.set({ showChecks: v })} />
      <Toggle label={t("settings.weather")} checked={prefs.weather} onChange={(v) => prefs.set({ weather: v })} />
    </div>
  );
}

function AudioSettings() {
  const { t, lang } = useT();
  const prefs = usePrefs();
  const volId = useId();
  const voiceId = useId();
  const [voices, setVoices] = useState(narrator.voices(lang));
  useEffect(() => {
    if (!narrator.available) return;
    const update = () => setVoices(narrator.voices(lang));
    update();
    window.speechSynthesis.addEventListener("voiceschanged", update);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", update);
  }, [lang]);
  return (
    <div className="space-y-4">
      <Toggle label={t("settings.audioOn")} checked={prefs.audio} onChange={(v) => prefs.set({ audio: v })} />
      <Field id={volId} label={`${t("settings.volume")}: ${Math.round(prefs.volume * 100)}%`}>
        <input id={volId} type="range" min={0} max={1} step={0.05} value={prefs.volume} onChange={(e) => prefs.set({ volume: Number(e.target.value) })} className="w-full accent-[var(--c-accent)]" />
      </Field>
      {narrator.available ? (
        <>
          <Toggle label={t("settings.tts")} checked={prefs.tts} onChange={(v) => { prefs.set({ tts: v }); if (!v) narrator.cancel(); }} />
          <Field id={voiceId} label={t("settings.voice")}>
            <select id={voiceId} className={inputClass} value={prefs.voiceURI} onChange={(e) => prefs.set({ voiceURI: e.target.value })}>
              <option value="">{t("settings.voiceDefault")}</option>
              {voices.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
          </Field>
        </>
      ) : (
        <p className="text-sm text-muted">{t("settings.ttsUnavailable")}</p>
      )}
    </div>
  );
}

function LanguageSettings() {
  const { t, lang } = useT();
  const set = usePrefs((s) => s.set);
  const game = useGame((s) => s.game);
  const setGame = useGame((s) => s.setGame);
  const reloadFeed = useGame((s) => s.reloadFeed);
  const toast = useGame((s) => s.toast);
  return (
    <ChoiceGroup
      legend={t("settings.language")}
      options={LANGS.map((l) => ({ value: l, label: optionText(l, "language", l).label }))}
      value={lang}
      onChange={(l) => {
        set({ language: l });
        if (game) {
          void api
            .updateGame(game.id, { settings: { ...game.settings, language: l } })
            .then((view) => {
              setGame(view);
              return reloadFeed();
            })
            .catch((e) => toast("error", errorCode(e)));
        }
      }}
    />
  );
}
