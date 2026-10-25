/**
 * Procedural ambience with the Web Audio API: rain/wind made from filtered noise and
 * small synthesized chimes. No audio files, so there is nothing to license or download.
 * Audio starts only after the player enables it (browsers also require a user gesture).
 */
type Palette = "cafe" | "city" | "forest";

const PROFILES: Record<Palette, { freq: number; q: number; gain: number; hum: number }> = {
  cafe: { freq: 1400, q: 0.6, gain: 0.32, hum: 0.05 },
  city: { freq: 2200, q: 0.5, gain: 0.38, hum: 0.02 },
  forest: { freq: 650, q: 0.8, gain: 0.26, hum: 0.0 },
};

class Ambient {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private filter: BiquadFilterNode | null = null;
  private noiseGain: GainNode | null = null;
  private humGain: GainNode | null = null;
  private source: AudioBufferSourceNode | null = null;
  private chimeTimer: ReturnType<typeof setTimeout> | null = null;
  private palette: Palette = "cafe";

  get running(): boolean {
    return this.ctx?.state === "running";
  }

  async start(palette: Palette, volume: number): Promise<void> {
    if (typeof AudioContext === "undefined") return;
    if (!this.ctx) this.build();
    await this.ctx!.resume();
    this.setPalette(palette);
    this.setVolume(volume);
    this.scheduleChimes();
  }

  stop(): void {
    if (this.chimeTimer) clearTimeout(this.chimeTimer);
    this.chimeTimer = null;
    void this.ctx?.suspend();
  }

  setVolume(volume: number): void {
    if (this.master && this.ctx) this.master.gain.setTargetAtTime(volume * 0.6, this.ctx.currentTime, 0.3);
  }

  setPalette(palette: Palette): void {
    this.palette = palette;
    if (!this.ctx || !this.filter || !this.noiseGain || !this.humGain) return;
    const p = PROFILES[palette];
    const t = this.ctx.currentTime;
    this.filter.frequency.setTargetAtTime(p.freq, t, 1.2);
    this.filter.Q.setTargetAtTime(p.q, t, 1.2);
    this.noiseGain.gain.setTargetAtTime(p.gain, t, 1.2);
    this.humGain.gain.setTargetAtTime(p.hum, t, 1.2);
  }

  /** A short rising arpeggio for good news (quest completed, achievement). */
  chime(): void {
    if (!this.ctx || !this.master || this.ctx.state !== "running") return;
    [523.25, 659.25, 783.99].forEach((f, i) => this.tone(f, this.ctx!.currentTime + i * 0.12, 0.9, 0.18));
  }

  private tone(freq: number, at: number, length: number, level: number): void {
    const ctx = this.ctx!;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(level, at + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, at + length);
    osc.connect(g).connect(this.master!);
    osc.start(at);
    osc.stop(at + length + 0.05);
  }

  private scheduleChimes(): void {
    if (this.chimeTimer) clearTimeout(this.chimeTimer);
    const next = 9000 + Math.random() * 16000;
    this.chimeTimer = setTimeout(() => {
      if (this.running && this.ctx) {
        const base = this.palette === "forest" ? 1174.66 : this.palette === "cafe" ? 880 : 0;
        if (base) this.tone(base * (Math.random() < 0.5 ? 1 : 0.75), this.ctx.currentTime, 1.6, 0.04);
      }
      this.scheduleChimes();
    }, next);
  }

  private build(): void {
    const ctx = new AudioContext();
    this.ctx = ctx;
    this.master = ctx.createGain();
    this.master.gain.value = 0;
    this.master.connect(ctx.destination);

    // Two seconds of pink-ish noise, looped.
    const buffer = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let b0 = 0;
    let b1 = 0;
    let b2 = 0;
    for (let i = 0; i < data.length; i++) {
      const white = Math.random() * 2 - 1;
      b0 = 0.99765 * b0 + white * 0.099046;
      b1 = 0.963 * b1 + white * 0.2965164;
      b2 = 0.57 * b2 + white * 1.0526913;
      data[i] = (b0 + b1 + b2 + white * 0.1848) * 0.11;
    }
    this.source = ctx.createBufferSource();
    this.source.buffer = buffer;
    this.source.loop = true;
    this.filter = ctx.createBiquadFilter();
    this.filter.type = "bandpass";
    this.noiseGain = ctx.createGain();
    this.source.connect(this.filter).connect(this.noiseGain).connect(this.master);
    this.source.start();

    const hum = ctx.createOscillator();
    hum.type = "sine";
    hum.frequency.value = 98;
    this.humGain = ctx.createGain();
    this.humGain.gain.value = 0;
    hum.connect(this.humGain).connect(this.master);
    hum.start();
  }
}

export const ambient = new Ambient();
