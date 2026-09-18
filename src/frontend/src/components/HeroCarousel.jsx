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

// Labeled technical-schematic backdrops, one per slide theme — boxes, wires,
// and connector pins in a blueprint style, drawn with currentColor so they
// recolor automatically with --hero-accent / the light-dark theme.
function SchematicBox({ x, y, w, h, label }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx="6" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <text x={x + w / 2} y={y + h / 2 + 4} textAnchor="middle" fontSize="11" fontWeight="700" fill="currentColor" letterSpacing="0.5">
        {label}
      </text>
    </g>
  );
}

function SchematicWire({ points }) {
  return <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 4" />;
}

function SchematicPin({ x, y }) {
  return <circle cx={x} cy={y} r="3" fill="currentColor" />;
}

function BlueprintGrid({ id }) {
  return (
    <>
      <defs>
        <pattern id={id} width="26" height="26" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="1" fill="currentColor" />
        </pattern>
      </defs>
      <rect width="600" height="320" fill={`url(#${id})`} opacity="0.5" />
    </>
  );
}

function PipelineArt() {
  return (
    <svg viewBox="0 0 600 320" className="hero__art-svg" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <BlueprintGrid id="hg-pipeline" />
      <SchematicBox x={250} y={64} w={100} h={46} label="INGEST" />
      <SchematicBox x={400} y={64} w={100} h={46} label="MODEL" />
      <SchematicBox x={400} y={208} w={100} h={46} label="REPORT" />
      <SchematicBox x={250} y={208} w={100} h={46} label="PLAN" />
      <SchematicWire points="350,87 400,87" />
      <SchematicWire points="450,110 450,208" />
      <SchematicWire points="400,231 350,231" />
      <SchematicWire points="300,110 300,208" />
      <SchematicPin x={400} y={87} />
      <SchematicPin x={450} y={110} />
      <SchematicPin x={450} y={208} />
      <SchematicPin x={300} y={110} />
      <SchematicPin x={300} y={208} />
      <SchematicPin x={350} y={231} />
    </svg>
  );
}

function SolarArt() {
  return (
    <svg viewBox="0 0 600 320" className="hero__art-svg" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <BlueprintGrid id="hg-solar" />
      <SchematicBox x={330} y={40} w={220} h={54} label="SOLAR PANELS" />
      <SchematicBox x={370} y={140} w={140} h={44} label="INVERTER" />
      <SchematicBox x={330} y={230} w={110} h={50} label="STORAGE" />
      <SchematicBox x={460} y={230} w={110} h={50} label="GRID" />
      <SchematicWire points="440,94 440,140" />
      <SchematicWire points="440,184 385,184 385,230" />
      <SchematicWire points="440,184 515,184 515,230" />
      <SchematicPin x={440} y={94} />
      <SchematicPin x={440} y={184} />
      <SchematicPin x={385} y={230} />
      <SchematicPin x={515} y={230} />
    </svg>
  );
}

function ImpactArt() {
  return (
    <svg viewBox="0 0 600 320" className="hero__art-svg" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <BlueprintGrid id="hg-impact" />
      <SchematicBox x={300} y={60} w={130} h={44} label="BASELINE" />
      <SchematicBox x={300} y={220} w={130} h={44} label="OPTIMIZED" />
      <SchematicBox x={470} y={140} w={100} h={44} label="AVOIDED" />
      <SchematicWire points="365,104 365,220" />
      <SchematicWire points="430,242 470,242 470,184" />
      <SchematicPin x={365} y={104} />
      <SchematicPin x={365} y={220} />
      <SchematicPin x={470} y={184} />
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

      <div className="hero__nav">
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
      </div>
    </section>
  );
}
