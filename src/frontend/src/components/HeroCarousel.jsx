import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Icon from "./ui/Icon.jsx";

const AUTOPLAY_MS = 6500;

const SLIDES = [
  {
    id: "pipeline",
    theme: "pipeline",
    eyebrow: "GridSentinel Pipeline",
    title: "FORECAST. DETECT. OPTIMIZE.",
    subtitle: "One LangGraph pipeline turns raw grid telemetry into a verified operator brief — end to end, every run.",
    primary: { label: "Start a Run", to: "/new-run" },
    secondary: { label: "See the Brief", to: "/brief" },
    steps: [
      { icon: "trendingUp", label: "Forecast" },
      { icon: "alertTriangle", label: "Detect" },
      { icon: "sliders", label: "Optimize" },
      { icon: "shieldCheck", label: "Verify" },
    ],
  },
  {
    id: "solar",
    theme: "solar",
    eyebrow: "Renewable Intelligence",
    title: "SUN TO GRID, TRACKED LIVE",
    subtitle: "CUSUM change-point detection flags real sustained drift in solar and wind output the moment it happens.",
    primary: { label: "Anomaly Intelligence", to: "/anomalies" },
    secondary: { label: "Curtailment Impact", to: "/curtailment" },
    steps: [
      { icon: "sun", label: "Sun" },
      { icon: "grid", label: "Panels" },
      { icon: "bolt", label: "Inverter" },
      { icon: "tower", label: "Grid" },
    ],
  },
  {
    id: "impact",
    theme: "impact",
    eyebrow: "Grid Stability",
    title: "MINIMIZE CURTAILMENT",
    subtitle: "An LP dispatch plan is benchmarked against a no-flexibility baseline to show exactly how much clean energy stays on the grid.",
    primary: { label: "Optimization Plan", to: "/optimization" },
    secondary: { label: "New Run", to: "/new-run" },
    steps: [
      { icon: "battery", label: "Storage" },
      { icon: "activity", label: "Dispatch" },
      { icon: "scissors", label: "Curtail" },
      { icon: "checkCircle", label: "Avoided" },
    ],
  },
];

// Abstract line-art backdrops, one per slide theme. Drawn with currentColor
// so they inherit --hero-accent and recolor automatically with the theme.
function PipelineArt() {
  const nodes = [
    [80, 60], [180, 40], [260, 110], [150, 150], [340, 70], [420, 140],
    [500, 60], [560, 150], [260, 220], [400, 240], [500, 260], [120, 240],
  ];
  const edges = [[0, 1], [1, 2], [2, 3], [3, 0], [2, 4], [4, 5], [5, 6], [6, 7], [3, 8], [8, 9], [9, 10], [8, 11]];
  return (
    <svg viewBox="0 0 600 320" className="hero__art-svg" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <g stroke="currentColor" strokeWidth="1">
        {edges.map(([a, b], i) => (
          <line key={i} x1={nodes[a][0]} y1={nodes[a][1]} x2={nodes[b][0]} y2={nodes[b][1]} />
        ))}
      </g>
      <g fill="currentColor">
        {nodes.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={i % 3 === 0 ? 5 : 3} />
        ))}
      </g>
    </svg>
  );
}

function SolarArt() {
  return (
    <svg viewBox="0 0 600 320" className="hero__art-svg" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <circle cx="500" cy="70" r="34" fill="currentColor" opacity="0.6" />
      <line x1="600" y1="230" x2="260" y2="230" stroke="currentColor" strokeWidth="1.5" />
      {[0, 1, 2].map((r) => (
        <g key={r} transform={`translate(${300 + r * 90} ${230 - r * 10}) rotate(-18)`}>
          {Array.from({ length: 4 }).map((_, c) => (
            <rect key={c} x={c * 34} y="0" width="28" height="60" rx="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
          ))}
        </g>
      ))}
    </svg>
  );
}

function ImpactArt() {
  const bars = [40, 70, 55, 95, 75];
  return (
    <svg viewBox="0 0 600 320" className="hero__art-svg" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <line x1="260" y1="260" x2="600" y2="260" stroke="currentColor" strokeWidth="1.5" />
      {bars.map((h, i) => (
        <rect key={i} x={300 + i * 55} y={260 - h * 1.6} width="34" height={h * 1.6} rx="3" fill="currentColor" opacity={0.35 + i * 0.09} />
      ))}
      <circle cx="580" cy="60" r="26" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M568 60 l8 8 16 -18" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const ART = {
  pipeline: PipelineArt,
  solar: SolarArt,
  impact: ImpactArt,
};

function FlowVisual({ steps }) {
  return (
    <div className="hero__flow" aria-hidden="true">
      {steps.map((s, i) => (
        <div className="hero__flow-item" key={s.label} style={{ animationDelay: `${i * 0.12}s` }}>
          <span className="hero__flow-node">
            <Icon name={s.icon} size={20} />
          </span>
          <span className="hero__flow-label">{s.label}</span>
        </div>
      ))}
    </div>
  );
}

function PlayGlyph() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 4v16l14-8Z" fill="currentColor" />
    </svg>
  );
}

function PauseGlyph() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 4h4v16H6zM14 4h4v16h-4z" fill="currentColor" />
    </svg>
  );
}

export default function HeroCarousel() {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!playing) return undefined;
    timerRef.current = setInterval(() => {
      setIndex((i) => (i + 1) % SLIDES.length);
    }, AUTOPLAY_MS);
    return () => clearInterval(timerRef.current);
  }, [playing, index]);

  const goTo = (next) => setIndex((next + SLIDES.length) % SLIDES.length);

  return (
    <section className="hero" onMouseEnter={() => setPlaying(false)} onMouseLeave={() => setPlaying(true)}>
      {SLIDES.map((slide, i) => {
        const Art = ART[slide.theme];
        return (
        <div
          key={slide.id}
          className={`hero__slide hero__slide--${slide.theme} ${i === index ? "is-active" : ""}`}
          aria-hidden={i !== index}
        >
          <div className="hero__backdrop">
            <span className="hero__glow hero__glow--a" />
            <span className="hero__glow hero__glow--b" />
            <div className="hero__art">
              <Art />
            </div>
          </div>

          <FlowVisual steps={slide.steps} />

          <div className="hero__content">
            <span className="hero__eyebrow">{slide.eyebrow}</span>
            <h2 className="hero__title">{slide.title}</h2>
            <p className="hero__subtitle">{slide.subtitle}</p>
            <div className="hero__ctas">
              <Link to={slide.primary.to} className="hero__btn hero__btn--primary">
                {slide.primary.label}
              </Link>
              <Link to={slide.secondary.to} className="hero__btn hero__btn--secondary">
                {slide.secondary.label}
              </Link>
            </div>
          </div>
        </div>
        );
      })}

      <div className="hero__controls">
        <button type="button" className="hero__control-btn" onClick={() => setPlaying((p) => !p)} aria-label={playing ? "Pause slideshow" : "Play slideshow"}>
          {playing ? <PauseGlyph /> : <PlayGlyph />}
        </button>
        <button type="button" className="hero__control-btn" onClick={() => goTo(index - 1)} aria-label="Previous slide">
          <Icon name="chevronRight" size={14} style={{ transform: "rotate(180deg)" }} />
        </button>
        <button type="button" className="hero__control-btn" onClick={() => goTo(index + 1)} aria-label="Next slide">
          <Icon name="chevronRight" size={14} />
        </button>
      </div>

      <div className="hero__dots">
        {SLIDES.map((s, i) => (
          <button
            key={s.id}
            type="button"
            className={`hero__dot ${i === index ? "is-active" : ""}`}
            onClick={() => setIndex(i)}
            aria-label={`Go to slide ${i + 1}: ${s.title}`}
          />
        ))}
      </div>
    </section>
  );
}
