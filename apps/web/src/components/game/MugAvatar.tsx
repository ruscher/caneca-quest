import { useId } from "react";
import type { Drink, Mug, Style } from "../../api/types";

const DRINK_COLORS: Record<Drink, { liquid: string; foam?: string }> = {
  black_coffee: { liquid: "#3b2416" },
  latte: { liquid: "#b98a5e" },
  cappuccino: { liquid: "#a87750", foam: "#efe3cf" },
  hot_chocolate: { liquid: "#5a2d1a" },
  tea: { liquid: "#b5682a" },
};

function shade(hex: string, amount: number): string {
  const n = parseInt(hex.slice(1), 16);
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) =>
    Math.round(amount < 0 ? c * (1 + amount) : c + (255 - c) * amount),
  );
  return `#${ch.map((c) => c.toString(16).padStart(2, "0")).join("")}`;
}

function luminance(hex: string): number {
  const n = parseInt(hex.slice(1), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}

export interface MugState {
  temperature?: number;
  integrity?: number;
  energy?: number;
  hidden?: boolean;
}

/** Original vector portrait of the player's mug, reacting to its condition. */
export function MugAvatar({
  mug,
  state = {},
  size = 120,
  label,
  animated = true,
}: {
  mug: Pick<Mug, "color" | "style" | "drink">;
  state?: MugState;
  size?: number;
  label: string;
  animated?: boolean;
}) {
  const uid = useId().replace(/:/g, "");
  const body = mug.color;
  const outline = shade(body, -0.45);
  const light = luminance(body) > 0.55;
  const pattern = light ? shade(body, -0.35) : shade(body, 0.55);
  const drink = DRINK_COLORS[mug.drink];
  const temp = state.temperature ?? 80;
  const integrity = state.integrity ?? 100;
  const tired = (state.energy ?? 100) < 15;
  const cold = temp < 25;
  const steamOpacity = Math.max(0, Math.min(0.85, (temp - 35) / 50));
  const faceColor = light ? "#2b1f17" : "#fbf3e6";

  return (
    <svg
      viewBox="0 0 120 120"
      width={size}
      height={size}
      role="img"
      aria-label={label}
      style={{ animation: cold && animated ? "shiver 0.25s linear infinite" : undefined }}
    >
      <defs>
        <clipPath id={`body-${uid}`}>
          <path d="M24 38 Q24 36 26 36 H84 Q86 36 86 38 L82 96 Q81 102 74 102 H36 Q29 102 28 96 Z" />
        </clipPath>
        <linearGradient id={`shine-${uid}`} x1="0" x2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.28" />
          <stop offset="0.35" stopColor="#fff" stopOpacity="0.05" />
          <stop offset="1" stopColor="#000" stopOpacity="0.12" />
        </linearGradient>
      </defs>

      <ellipse cx="56" cy="106" rx="34" ry="5" fill="#000" opacity="0.18" />

      {steamOpacity > 0 && (
        <g
          fill="none"
          stroke={light ? "#8a7a6a" : "#d8cfc4"}
          strokeWidth="2.4"
          strokeLinecap="round"
          style={{ ["--steam-opacity" as string]: String(steamOpacity) }}
          opacity={animated ? undefined : steamOpacity}
        >
          {[40, 55, 70].map((x, i) => (
            <path
              key={x}
              d={`M${x} 30 q-5 -6 0 -12 q5 -6 0 -12`}
              style={animated ? { animation: `steam 2.8s ease-in-out ${i * 0.7}s infinite` } : undefined}
            />
          ))}
        </g>
      )}

      {/* handle */}
      <path
        d="M84 48 Q104 46 104 64 Q104 84 80 86"
        fill="none"
        stroke={outline}
        strokeWidth="11"
        strokeLinecap="round"
      />
      <path
        d="M84 48 Q104 46 104 64 Q104 84 80 86"
        fill="none"
        stroke={body}
        strokeWidth="7"
        strokeLinecap="round"
      />

      {/* body */}
      <path
        d="M24 38 Q24 36 26 36 H84 Q86 36 86 38 L82 96 Q81 102 74 102 H36 Q29 102 28 96 Z"
        fill={body}
        stroke={outline}
        strokeWidth="2.5"
      />
      <g clipPath={`url(#body-${uid})`}>
        <Pattern style={mug.style} color={pattern} />
        <rect x="20" y="30" width="70" height="80" fill={`url(#shine-${uid})`} />
        {integrity <= 50 && (
          <path
            d="M70 40 l-6 12 l7 6 l-8 14 l5 6"
            fill="none"
            stroke={outline}
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
        )}
        {integrity <= 20 && (
          <path
            d="M34 52 l8 10 l-6 8 l9 12 M50 96 l4 -10 l-5 -6"
            fill="none"
            stroke={outline}
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
        )}
      </g>

      {/* rim and drink */}
      <ellipse cx="55" cy="37" rx="31" ry="6" fill={shade(body, -0.15)} stroke={outline} strokeWidth="2.5" />
      <ellipse cx="55" cy="37.5" rx="26" ry="4.2" fill={drink.liquid} />
      {drink.foam && <ellipse cx="55" cy="37" rx="20" ry="3" fill={drink.foam} opacity="0.95" />}
      {mug.style === "classic" && (
        <ellipse cx="55" cy="37" rx="31" ry="6" fill="none" stroke="#c9a24a" strokeWidth="1.2" />
      )}

      {/* face */}
      <g fill={faceColor} stroke={faceColor}>
        {state.hidden ? (
          <path d="M42 64 q4 3 8 0 M60 64 q4 3 8 0" fill="none" strokeWidth="2" strokeLinecap="round" />
        ) : tired ? (
          <path d="M42 65 h8 M60 65 h8" strokeWidth="2.2" strokeLinecap="round" />
        ) : (
          <>
            <ellipse cx="46" cy="63" rx="2.6" ry="3.4" stroke="none" />
            <ellipse cx="64" cy="63" rx="2.6" ry="3.4" stroke="none" />
          </>
        )}
        <path
          d={cold || integrity <= 20 ? "M49 76 q6 -4 12 0" : "M48 73 q7 6 14 0"}
          fill="none"
          strokeWidth="2.2"
          strokeLinecap="round"
        />
        <circle cx="40" cy="70" r="3" fill="#e8908a" stroke="none" opacity={light ? 0.5 : 0.35} />
        <circle cx="70" cy="70" r="3" fill="#e8908a" stroke="none" opacity={light ? 0.5 : 0.35} />
      </g>
    </svg>
  );
}

function Pattern({ style, color }: { style: Style; color: string }) {
  switch (style) {
    case "striped":
      return (
        <g fill={color} opacity="0.55">
          {[46, 60, 74, 88].map((y) => (
            <rect key={y} x="18" y={y} width="80" height="5" />
          ))}
        </g>
      );
    case "dotted":
      return (
        <g fill={color} opacity="0.6">
          {[
            [32, 48], [48, 50], [66, 46], [78, 56], [36, 84], [56, 90], [74, 82], [30, 66], [80, 72],
          ].map(([x, y]) => (
            <circle key={`${x}-${y}`} cx={x} cy={y} r="3.2" />
          ))}
        </g>
      );
    case "floral":
      return (
        <g fill={color} opacity="0.7">
          {[
            [34, 50], [74, 54], [40, 88], [70, 88],
          ].map(([x, y]) => (
            <g key={`${x}-${y}`} transform={`translate(${x} ${y})`}>
              {[0, 72, 144, 216, 288].map((a) => (
                <ellipse key={a} cx="0" cy="-4" rx="2.4" ry="3.6" transform={`rotate(${a})`} />
              ))}
              <circle r="1.8" fill="#e9c46a" />
            </g>
          ))}
        </g>
      );
    case "minimal":
      return <rect x="18" y="86" width="80" height="2.5" fill={color} opacity="0.6" />;
    case "rustic":
      return (
        <g fill={color} opacity="0.5">
          {Array.from({ length: 26 }, (_, i) => (
            <circle key={i} cx={26 + ((i * 37) % 58)} cy={42 + ((i * 53) % 58)} r={0.9 + (i % 3) * 0.5} />
          ))}
        </g>
      );
    default:
      return null;
  }
}
