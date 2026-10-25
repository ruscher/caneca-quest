/**
 * Read-aloud narrator. The interface keeps the game independent of the engine used:
 * the default uses the browser's Web Speech API; a future local TTS (e.g. served by the
 * backend) only needs to implement SpeechNarrator.
 */
export interface SpeechNarrator {
  readonly available: boolean;
  voices(lang: string): { id: string; name: string }[];
  speak(text: string, lang: string, voiceId?: string): void;
  cancel(): void;
}

class WebSpeechNarrator implements SpeechNarrator {
  get available(): boolean {
    return typeof window !== "undefined" && "speechSynthesis" in window;
  }

  voices(lang: string) {
    if (!this.available) return [];
    const prefix = lang.slice(0, 2).toLowerCase();
    return window.speechSynthesis
      .getVoices()
      .filter((v) => v.lang.toLowerCase().startsWith(prefix))
      .map((v) => ({ id: v.voiceURI, name: `${v.name} (${v.lang})` }));
  }

  speak(text: string, lang: string, voiceId?: string): void {
    if (!this.available || !text.trim()) return;
    const synth = window.speechSynthesis;
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text.replace(/[—“”"]/g, " "));
    utterance.lang = lang;
    utterance.rate = 1;
    const voice = synth.getVoices().find((v) => v.voiceURI === voiceId);
    if (voice) utterance.voice = voice;
    synth.speak(utterance);
  }

  cancel(): void {
    if (this.available) window.speechSynthesis.cancel();
  }
}

export const narrator: SpeechNarrator = new WebSpeechNarrator();
