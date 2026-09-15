// Minimal inline SVG icon set (stroke-based, ~feather style). No external
// icon library dependency — kept purely presentational.

const paths = {
  bolt: "M13 2 3 14h7l-1 8 10-12h-7l1-8Z",
  dollar: "M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6",
  wind: "M9.6 4.6A2 2 0 1 1 11 8H2m10.6 11.4A2 2 0 1 0 14 16H2m15.6-7.4A2.5 2.5 0 1 1 19.5 13H2",
  alertTriangle: "M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0ZM12 9v4M12 17h.01",
  shieldCheck: "M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5l-8-3Zm-3 10 2 2 4-4",
  checkCircle: "M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4 12 14.01l-3-3",
  download: "M12 3v12m0 0-4-4m4 4 4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2",
  bell: "M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9ZM13.73 21a2 2 0 0 1-3.46 0",
  settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7.4-3a7.4 7.4 0 0 1-.1 1.2l2 1.6-2 3.4-2.3-1a7.6 7.6 0 0 1-2.1 1.2l-.4 2.6H9.5l-.4-2.6a7.6 7.6 0 0 1-2.1-1.2l-2.3 1-2-3.4 2-1.6A7.4 7.4 0 0 1 4.6 12c0-.4 0-.8.1-1.2l-2-1.6 2-3.4 2.3 1c.6-.5 1.3-.9 2.1-1.2L9.5 3h5l.4 2.6c.8.3 1.5.7 2.1 1.2l2.3-1 2 3.4-2 1.6c.1.4.1.8.1 1.2Z",
  user: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z",
  menu: "M3 6h18M3 12h18M3 18h18",
  chevronRight: "m9 6 6 6-6 6",
  activity: "M22 12h-4l-3 9L9 3l-3 9H2",
  fileText: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Zm0 0v6h6M8 13h8M8 17h8M8 9h2",
  grid: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
  sliders: "M4 21v-7M4 10V3m8 18v-9m0-4V3m8 18v-5m0-4V3M1 14h6M9 8h6M17 16h6",
  trendingUp: "M23 6 13.5 15.5l-5-5L1 18M17 6h6v6",
  sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10ZM12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42",
  cloudLightning: "M19 16.9A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.3M13 11l-4 6h6l-4 6",
  layers: "m12 2 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5m-18 5 9 5 9-5",
  battery: "M15 7H3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2ZM21 11v2",
  scissors: "M6 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm0 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm14.5-16-11 11m0-6 11 11",
  overview: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
  minus: "M5 12h14",
  plus: "M12 5v14M5 12h14",
};

export default function Icon({ name, size = 18, strokeWidth = 1.8, className, style }) {
  const d = paths[name];
  if (!d) return null;
  return (
    <svg
      className={className}
      style={style}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}
