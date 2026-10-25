import { useEffect, useState } from "react";
import { ambient } from "./audio/ambient";
import { type Palette, SceneBackdrop } from "./components/game/SceneBackdrop";
import { Toasts } from "./components/ui/Toasts";
import { CreateScreen } from "./screens/CreateScreen";
import { GameScreen } from "./screens/GameScreen";
import { CreditsScreen, HelpScreen } from "./screens/InfoScreens";
import { SavesScreen } from "./screens/SavesScreen";
import { SettingsDialog } from "./screens/SettingsDialog";
import { WelcomeScreen } from "./screens/WelcomeScreen";
import { narrator } from "./speech/narrator";
import { useGame } from "./store/game";
import { prefersReducedMotion, resolvedTheme, usePrefs } from "./store/prefs";

function useSystemTheme() {
  const [, force] = useState(0);
  useEffect(() => {
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const update = () => force((n) => n + 1);
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
}

export function App() {
  useSystemTheme();
  const screen = useGame((s) => s.screen);
  const palette = (useGame((s) => s.game?.region.palette) ?? "cafe") as Palette;
  const narration = useGame((s) => s.narration);
  const toasts = useGame((s) => s.toasts);
  const prefs = usePrefs();
  const theme = resolvedTheme(prefs.theme);
  const reduced = prefersReducedMotion(prefs.motion);

  // Reflect preferences on the document (theme, motion, font, size, language).
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.dataset.motion = prefs.motion === "auto" ? "" : prefs.motion;
    root.dataset.readingFont = prefs.readingFont;
    root.style.setProperty("--font-scale", String(prefs.fontScale));
    root.lang = prefs.language;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#12161f" : "#f6efe3");
  }, [theme, prefs.motion, prefs.readingFont, prefs.fontScale, prefs.language]);

  useEffect(() => {
    if (prefs.audio) void ambient.start(palette, prefs.volume);
    else ambient.stop();
  }, [prefs.audio, palette, prefs.volume]);

  useEffect(() => {
    if (prefs.audio && toasts.some((t) => t.kind === "achievement" || t.kind === "success")) ambient.chime();
  }, [toasts, prefs.audio]);

  useEffect(() => {
    if (prefs.tts && narration) narrator.speak(narration.text, prefs.language, prefs.voiceURI || undefined);
  }, [narration, prefs.tts, prefs.language, prefs.voiceURI]);

  return (
    <>
      <SceneBackdrop palette={palette} theme={theme} weather={prefs.weather} reducedMotion={reduced} />
      {screen === "welcome" && <WelcomeScreen />}
      {screen === "create" && <CreateScreen />}
      {screen === "game" && <GameScreen />}
      {screen === "saves" && <SavesScreen />}
      {screen === "help" && <HelpScreen />}
      {screen === "credits" && <CreditsScreen />}
      <SettingsDialog />
      <Toasts />
    </>
  );
}
