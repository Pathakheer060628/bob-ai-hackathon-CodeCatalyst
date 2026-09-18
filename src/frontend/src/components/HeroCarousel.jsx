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
      {SLIDES.map((slide, i) => (
        <div
          key={slide.id}
          className={`hero__slide hero__slide--${slide.theme} ${i === index ? "is-active" : ""}`}
          aria-hidden={i !== index}
        >
          <div className="hero__backdrop">
            <span className="hero__glow hero__glow--a" />
            <span className="hero__glow hero__glow--b" />
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
      ))}

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
