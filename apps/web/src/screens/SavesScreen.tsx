import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { Checkpoint, GameSummary } from "../api/types";
import { MugAvatar } from "../components/game/MugAvatar";
import { Button, Dialog, inputClass } from "../components/ui/primitives";
import { relativeTime, useT } from "../i18n";
import { errorCode, useGame } from "../store/game";

type Confirm = { text: string; action: () => Promise<void> } | null;

export function SavesScreen() {
  const { t, lang } = useT();
  const go = useGame((s) => s.go);
  const current = useGame((s) => s.game);
  const openGame = useGame((s) => s.openGame);
  const setGame = useGame((s) => s.setGame);
  const reloadFeed = useGame((s) => s.reloadFeed);
  const toast = useGame((s) => s.toast);
  const [games, setGames] = useState<GameSummary[]>([]);
  const [picked, setSelected] = useState<string | null>(current?.id ?? null);
  const [checkpointData, setCheckpoints] = useState<{ game: string; list: Checkpoint[] } | null>(null);
  const [version, setVersion] = useState(0);
  const [confirm, setConfirm] = useState<Confirm>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  // The selection falls back to the first game when the picked one disappears.
  const selected = games.some((g) => g.id === picked) ? picked : (games[0]?.id ?? null);
  const checkpoints = checkpointData && checkpointData.game === selected ? checkpointData.list : [];
  const refresh = () => setVersion((v) => v + 1);
  const reloadCheckpoints = useCallback(
    (gameId: string) =>
      api
        .checkpoints(gameId)
        .then((list) => setCheckpoints({ game: gameId, list }))
        .catch((err) => toast("error", errorCode(err))),
    [toast],
  );

  useEffect(() => {
    api
      .listGames()
      .then(setGames)
      .catch((err) => toast("error", errorCode(err)));
  }, [version, toast]);

  useEffect(() => {
    if (selected) void reloadCheckpoints(selected);
  }, [selected, version, reloadCheckpoints]);

  const guard = (fn: () => Promise<void>) => async () => {
    try {
      await fn();
    } catch (err) {
      toast("error", errorCode(err));
    }
  };

  const exportGame = guard(async () => {
    if (!selected) return;
    const data = await api.exportGame(selected);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const name = games.find((g) => g.id === selected)?.name ?? "aventura";
    a.href = url;
    a.download = `caneca-quest-${name.replace(/[^\w-]+/g, "_")}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  });

  const importFile = async (file: File) => {
    if (file.size > 8 * 1024 * 1024) {
      toast("error", "payload_too_large");
      return;
    }
    try {
      const view = await api.importGame(await file.text());
      toast("success", `raw:${t("saves.importOk")}`);
      setSelected(view.id);
      refresh();
    } catch (err) {
      toast("error", errorCode(err));
    }
  };

  const backup = guard(async () => {
    const r = await api.backup();
    toast("success", `raw:${t("saves.backupDone", { file: r.file })}`);
  });

  const sel = games.find((g) => g.id === selected);

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-3xl font-semibold">{t("saves.title")}</h1>
        <div className="flex flex-wrap gap-2">
          <Button icon="upload" onClick={() => fileRef.current?.click()}>
            {t("saves.import")}
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void importFile(f);
              e.target.value = "";
            }}
          />
          <Button icon="shield" onClick={() => void backup()}>
            {t("saves.backup")}
          </Button>
          <Button icon="chevronLeft" onClick={() => go(current ? "game" : "welcome")}>
            {t("create.back")}
          </Button>
        </div>
      </div>

      {games.length === 0 ? (
        <p className="mt-10 text-center text-muted">{t("saves.empty")}</p>
      ) : (
        <div className="mt-6 grid gap-5 md:grid-cols-[1fr_1fr]">
          <ul className="space-y-2" aria-label={t("saves.title")}>
            {games.map((g) => (
              <li key={g.id}>
                <div
                  className={`card flex items-center gap-3 p-3 ${g.id === selected ? "ring-2 ring-accent" : ""}`}
                >
                  <MugAvatar mug={g.mug} size={56} label={g.mug.name} animated={false} />
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-left"
                    onClick={() => setSelected(g.id)}
                    aria-pressed={g.id === selected}
                  >
                    <p className="truncate font-semibold">{g.name}</p>
                    <p className="truncate text-sm text-muted">
                      {t("saves.chapter", { n: g.chapter })} · {g.location} · {t("saves.level", { n: g.level })}
                    </p>
                    <p className="text-xs text-muted">{t("saves.updated", { when: relativeTime(lang, g.updated_at) })}</p>
                  </button>
                  <Button variant="primary" onClick={guard(() => openGame(g.id))}>
                    {t("saves.open")}
                  </Button>
                </div>
              </li>
            ))}
          </ul>

          {sel && (
            <section className="card space-y-4 p-4" aria-labelledby="sel-title">
              <h2 id="sel-title" className="font-display text-xl font-semibold">
                {sel.name}
              </h2>
              {renaming === sel.id ? (
                <form
                  className="flex gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void guard(async () => {
                      await api.updateGame(sel.id, { name: newName.trim() });
                      setRenaming(null);
                      refresh();
                    })();
                  }}
                >
                  <label htmlFor="rename" className="sr-only">
                    {t("saves.rename")}
                  </label>
                  <input id="rename" className={inputClass} value={newName} maxLength={80} onChange={(e) => setNewName(e.target.value)} />
                  <Button type="submit" variant="primary" disabled={!newName.trim()}>
                    {t("saves.confirm")}
                  </Button>
                </form>
              ) : (
                <div className="flex flex-wrap gap-2">
                  <Button icon="feather" onClick={() => { setRenaming(sel.id); setNewName(sel.name); }}>
                    {t("saves.rename")}
                  </Button>
                  <Button icon="download" onClick={() => void exportGame()}>
                    {t("saves.export")}
                  </Button>
                  <Button
                    icon="trash"
                    variant="danger"
                    onClick={() =>
                      setConfirm({
                        text: t("saves.deleteConfirm", { name: sel.name }),
                        action: async () => {
                          await api.deleteGame(sel.id);
                          if (current?.id === sel.id) useGame.getState().closeGame();
                          setSelected(null);
                          refresh();
                        },
                      })
                    }
                  >
                    {t("saves.delete")}
                  </Button>
                </div>
              )}

              <div>
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-display text-lg font-semibold">{t("saves.checkpoints")}</h3>
                  <Button
                    icon="save"
                    onClick={guard(async () => {
                      await api.createCheckpoint(sel.id, `${sel.location} · ${t("saves.turn", { n: sel.turn })}`);
                      await reloadCheckpoints(sel.id);
                    })}
                  >
                    {t("saves.createCheckpoint")}
                  </Button>
                </div>
                {checkpoints.length === 0 ? (
                  <p className="mt-2 text-sm text-muted">{t("saves.noCheckpoints")}</p>
                ) : (
                  <ul className="mt-2 space-y-1.5">
                    {checkpoints.map((cp) => (
                      <li key={cp.id} className="flex items-center gap-2 rounded-lg bg-surface-2 px-3 py-2">
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold">{cp.label}</p>
                          <p className="text-xs text-muted">
                            {t("saves.turn", { n: cp.turn })}
                            {cp.auto ? ` · ${t("saves.auto")}` : ""} · {relativeTime(lang, cp.created_at)}
                          </p>
                        </div>
                        <Button
                          className="min-h-9 px-3 text-sm"
                          onClick={() =>
                            setConfirm({
                              text: t("saves.restoreConfirm", { label: cp.label, turn: cp.turn }),
                              action: async () => {
                                const view = await api.restoreCheckpoint(sel.id, cp.id);
                                if (current?.id === sel.id) {
                                  setGame(view);
                                  await reloadFeed();
                                  go("game");
                                } else {
                                  await openGame(sel.id);
                                }
                              },
                            })
                          }
                        >
                          {t("saves.restore")}
                        </Button>
                        <button
                          type="button"
                          aria-label={`${t("saves.delete")}: ${cp.label}`}
                          className="inline-flex size-9 items-center justify-center rounded-lg text-muted hover:bg-surface hover:text-bad"
                          onClick={guard(async () => {
                            await api.deleteCheckpoint(sel.id, cp.id);
                            await reloadCheckpoints(sel.id);
                          })}
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>
          )}
        </div>
      )}

      <Dialog open={confirm !== null} onClose={() => setConfirm(null)} title={t("saves.confirm")} closeLabel={t("a11y.close")}>
        <p>{confirm?.text}</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button onClick={() => setConfirm(null)}>{t("saves.cancel")}</Button>
          <Button
            variant="danger"
            onClick={() => {
              const c = confirm;
              setConfirm(null);
              if (c) void guard(c.action)();
            }}
          >
            {t("saves.confirm")}
          </Button>
        </div>
      </Dialog>
    </main>
  );
}
