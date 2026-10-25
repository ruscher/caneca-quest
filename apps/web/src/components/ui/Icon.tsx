// Original line icons (24×24, stroke = currentColor). Decorative unless a title is given.
const PATHS: Record<string, string> = {
  settings:
    "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm7.4-2.1.1-1.4-.1-1.4 2-1.6-2-3.4-2.4 1a7 7 0 0 0-2.4-1.4L14.2 2h-4l-.4 2.7A7 7 0 0 0 7.4 6l-2.4-1-2 3.4 2 1.6-.1 1.4.1 1.4-2 1.6 2 3.4 2.4-1a7 7 0 0 0 2.4 1.4l.4 2.7h4l.4-2.7a7 7 0 0 0 2.4-1.4l2.4 1 2-3.4Z",
  menu: "M4 6h16M4 12h16M4 18h16",
  close: "M6 6l12 12M18 6 6 18",
  send: "M4 12 20 4l-6 16-3-7-7-1Z",
  stop: "M7 7h10v10H7z",
  map: "M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Zm0 0v14m6-12v14",
  bag: "M6 8h12l-1 12H7L6 8Zm3 0V6a3 3 0 0 1 6 0v2",
  scroll: "M7 4h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H8a3 3 0 0 1-3-3V6a2 2 0 0 1 2-2Zm2 5h6M9 13h6",
  book: "M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2V5Zm0 14a2 2 0 0 1 2-2h13",
  heart: "M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z",
  brain: "M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a3 3 0 0 0-3-1Zm6 0a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1",
  star: "m12 3 2.6 5.6 6 .7-4.5 4.1 1.2 6-5.3-3-5.3 3 1.2-6L3.4 9.3l6-.7L12 3Z",
  users: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm-6 9a6 6 0 0 1 12 0m1-9a3 3 0 1 0 0-6m2 15a5 5 0 0 0-3-4.6",
  chevronLeft: "m15 5-7 7 7 7",
  chevronRight: "m9 5 7 7-7 7",
  chevronDown: "m5 9 7 7 7-7",
  plus: "M12 5v14M5 12h14",
  download: "M12 4v11m0 0-4-4m4 4 4-4M5 19h14",
  upload: "M12 20V9m0 0-4 4m4-4 4 4M5 5h14",
  trash: "M5 7h14M10 11v6m4-6v6M7 7l1 13h8l1-13M9 7V4h6v3",
  save: "M5 4h11l3 3v13H5V4Zm3 0v5h7V4M8 20v-6h8v6",
  sun: "M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0-14v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  moon: "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z",
  volume: "M4 10v4h4l5 4V6L8 10H4Zm12-1a4 4 0 0 1 0 6m2-9a8 8 0 0 1 0 12",
  help: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm-2.5-11.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5V14m0 3h.01",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-10v6m0-9h.01",
  sparkle: "M12 3v4m0 10v4M3 12h4m10 0h4M6 6l2.5 2.5m7 7L18 18M6 18l2.5-2.5m7-7L18 6",
  compass: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm3.5-12.5-2 5-5 2 2-5 5-2Z",
  flame: "M12 21a6 6 0 0 0 6-6c0-4-3-6-4-10-1 2-2 3-4 4-2 1.5-4 3.5-4 6a6 6 0 0 0 6 6Zm0 0a2.5 2.5 0 0 1-2.5-2.5c0-1.5 1.5-2.5 2.5-4 1 1.5 2.5 2.5 2.5 4A2.5 2.5 0 0 1 12 21Z",
  droplet: "M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z",
  shield: "M12 3 5 6v5c0 4.5 3 8.2 7 10 4-1.8 7-5.5 7-10V6l-7-3Z",
  bolt: "M13 3 5 13h6l-1 8 8-10h-6l1-8Z",
  feather: "M20 4c-6 0-11 4-12 11l-3 5m3-5h6c4-1 6-5 6-11Z",
  dice: "M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Zm3.5 4h.01M15.5 8h.01M12 12h.01M8.5 16h.01m7-.01h.01",
  cup: "M5 8h11v6a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5V8Zm11 2h1.5a2.5 2.5 0 0 1 0 5H16M8 3c0 1 1 1 1 2s-1 1-1 2m4-4c0 1 1 1 1 2s-1 1-1 2",
  play: "M8 5v14l11-7L8 5Z",
  copy: "M8 8h11v12H8V8Zm-3 8V4h11",
  image: "M4 5h16v14H4V5Zm0 11 5-5 4 4 2-2 5 5M15 9h.01",
  door: "M6 3h12v18H6V3Zm8 9h.01",
  pin: "M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Zm0-8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
  key: "M15 10a4 4 0 1 0-3.5 4L10 15.5V18H7.5V20.5H4V17l5.6-5.6A4 4 0 0 0 15 10Zm1.5-2.5h.01",
  hourglass: "M7 3h10M7 21h10M8 3c0 5 8 5 8 9s-8 4-8 9m8-18c0 5-8 5-8 9s8 4 8 9",
};

export type IconName = keyof typeof PATHS;

export function Icon({
  name,
  size = 20,
  title,
  className,
}: {
  name: IconName;
  size?: number;
  title?: string;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}

/** Small glyphs for item/NPC icon ids coming from content. */
export const CONTENT_ICONS: Record<string, IconName> = {
  key: "key",
  map: "map",
  book: "book",
  letter: "scroll",
  photo: "image",
  gear: "settings",
  cat: "heart",
  radio: "volume",
  rat: "users",
  pigeon: "feather",
  can: "shield",
  grinder: "settings",
  sugarbowl: "cup",
  boat: "compass",
  feather: "feather",
  fish: "droplet",
  sugar: "sparkle",
  coin: "star",
  button: "star",
  string: "feather",
  cloth: "scroll",
  cap: "star",
  stick: "feather",
  bread: "cup",
  npc: "users",
  item: "bag",
};
