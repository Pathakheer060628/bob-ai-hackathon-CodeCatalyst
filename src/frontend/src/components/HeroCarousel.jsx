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
        <pattern id={id} width="22" height="22" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="1" fill="currentColor" />
        </pattern>
      </defs>
      <rect width="480" height="250" fill={`url(#${id})`} opacity="0.5" />
    </>
  );
}

// Every art box shares one 480x250 canvas with "meet" scaling, so it always
// renders fully and predictably -- no cropping math, and it lives inside a
// fixed corner box that never reaches the flow row pinned top-right.
function PipelineArt() {
  return (
    <svg viewBox="0 0 480 250" className="hero__art-svg" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <BlueprintGrid id="hg-pipeline" />
      <SchematicBox x={30} y={25} w={160} h={56} label="INGEST" />
      <SchematicBox x={290} y={25} w={160} h={56} label="MODEL" />
      <SchematicBox x={290} y={165} w={160} h={56} label="REPORT" />
      <SchematicBox x={30} y={165} w={160} h={56} label="PLAN" />
      <SchematicWire points="190,53 290,53" />
      <SchematicWire points="370,81 370,165" />
      <SchematicWire points="290,193 190,193" />
      <SchematicWire points="110,81 110,165" />
      <SchematicPin x={290} y={53} />
      <SchematicPin x={370} y={81} />
      <SchematicPin x={370} y={165} />
      <SchematicPin x={110} y={81} />
      <SchematicPin x={110} y={165} />
      <SchematicPin x={190} y={193} />
    </svg>
  );
}

function SolarArt() {
  return (
    <svg viewBox="0 0 480 250" className="hero__art-svg" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <BlueprintGrid id="hg-solar" />
      <SchematicBox x={140} y={10} w={200} h={54} label="SOLAR PANELS" />
      <SchematicBox x={165} y={100} w={150} h={48} label="INVERTER" />
      <SchematicBox x={40} y={186} w={130} h={52} label="STORAGE" />
      <SchematicBox x={300} y={186} w={130} h={52} label="GRID" />
      <SchematicWire points="240,64 240,100" />
      <SchematicWire points="240,148 105,148 105,186" />
      <SchematicWire points="240,148 365,148 365,186" />
      <SchematicPin x={240} y={64} />
      <SchematicPin x={240} y={148} />
      <SchematicPin x={105} y={186} />
      <SchematicPin x={365} y={186} />
    </svg>
  );
}

function ImpactArt() {
  return (
    <svg viewBox="0 0 480 250" className="hero__art-svg" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <BlueprintGrid id="hg-impact" />
      <SchematicBox x={30} y={20} w={170} h={54} label="BASELINE" />
      <SchematicBox x={30} y={176} w={170} h={54} label="OPTIMIZED" />
      <SchematicBox x={280} y={98} w={170} h={54} label="AVOIDED" />
      <SchematicWire points="115,74 115,176" />
      <SchematicWire points="200,203 365,203 365,152" />
      <SchematicPin x={115} y={74} />
      <SchematicPin x={115} y={176} />
      <SchematicPin x={365} y={152} />
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
