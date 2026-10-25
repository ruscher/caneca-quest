import { useEffect, useRef } from "react";

export type Palette = "cafe" | "city" | "forest";

const GRADIENTS: Record<Palette, { light: string; dark: string }> = {
  cafe: {
    light:
      "radial-gradient(120% 80% at 15% 0%, #fbe9cf 0%, transparent 60%), radial-gradient(90% 70% at 100% 100%, #ead6bb 0%, transparent 70%)",
    dark: "radial-gradient(100% 70% at 12% 0%, #3a2a1e 0%, transparent 60%), radial-gradient(90% 70% at 100% 100%, #16233a 0%, transparent 70%)",
  },
  city: {
    light:
      "radial-gradient(110% 80% at 85% 0%, #dfe7f0 0%, transparent 60%), radial-gradient(90% 60% at 0% 100%, #efe2cc 0%, transparent 70%)",
    dark: "radial-gradient(110% 80% at 85% 0%, #1b2c47 0%, transparent 60%), radial-gradient(90% 60% at 0% 100%, #2a2131 0%, transparent 70%)",
  },
  forest: {
    light:
      "radial-gradient(110% 80% at 50% 0%, #e1ead9 0%, transparent 60%), radial-gradient(90% 60% at 100% 100%, #efe4cf 0%, transparent 70%)",
    dark: "radial-gradient(110% 80% at 50% 0%, #15302a 0%, transparent 60%), radial-gradient(90% 60% at 100% 100%, #1d1c33 0%, transparent 70%)",
  },
};

interface Particle {
  x: number;
  y: number;
  v: number;
  len: number;
  phase: number;
}

/** Ambient background: palette gradient + subtle, low-cost weather particles. */
export function SceneBackdrop({
  palette,
  theme,
  weather,
  reducedMotion,
}: {
  palette: Palette;
  theme: "light" | "dark";
  weather: boolean;
  reducedMotion: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !weather || reducedMotion) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let raf = 0;
    let last = 0;
    let width = 0;
    let height = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const fireflies = palette === "forest";
    const count = fireflies ? 26 : 70;
    const particles: Particle[] = [];

    const resize = () => {
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        v: fireflies ? 6 + Math.random() * 10 : 380 + Math.random() * 320,
        len: fireflies ? 1.2 + Math.random() * 1.8 : 10 + Math.random() * 16,
        phase: Math.random() * Math.PI * 2,
      });
    }
    const rainColor = theme === "dark" ? "rgba(170,195,230,0.22)" : "rgba(70,90,120,0.16)";
    const glow = theme === "dark" ? "rgba(240,210,120," : "rgba(190,140,60,";

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (now - last < 33) return; // ~30 fps is plenty for ambience
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      ctx.clearRect(0, 0, width, height);
      if (fireflies) {
        for (const p of particles) {
          p.phase += dt * 1.3;
          p.y -= p.v * dt;
          p.x += Math.sin(p.phase) * 0.4;
          if (p.y < -10) {
            p.y = height + 10;
            p.x = Math.random() * width;
          }
          const a = 0.25 + 0.35 * (0.5 + 0.5 * Math.sin(p.phase * 2));
          ctx.beginPath();
          ctx.fillStyle = `${glow}${a.toFixed(2)})`;
          ctx.arc(p.x, p.y, p.len, 0, Math.PI * 2);
          ctx.fill();
        }
      } else {
        ctx.strokeStyle = rainColor;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (const p of particles) {
          p.y += p.v * dt;
          p.x -= p.v * dt * 0.12;
          if (p.y > height + 20) {
            p.y = -20;
            p.x = Math.random() * (width + 60);
          }
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p.x - p.len * 0.12, p.y - p.len);
        }
        ctx.stroke();
      }
    };
    const onVisibility = () => {
      cancelAnimationFrame(raf);
      if (!document.hidden) raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [palette, theme, weather, reducedMotion]);

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10">
      <div
        className="absolute inset-0 transition-[background] duration-1000"
        style={{ backgroundImage: GRADIENTS[palette][theme] }}
      />
      {weather && !reducedMotion && <canvas ref={canvasRef} className="absolute inset-0 size-full" />}
    </div>
  );
}
