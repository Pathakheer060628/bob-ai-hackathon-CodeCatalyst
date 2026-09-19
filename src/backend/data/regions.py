"""Static reference data for the regional power-distribution module.

This is separate from `grid_renewable_de_2017_2019.csv` (the real, hourly
ENTSO-E/OPSD time series everything else in GridSentinel is computed from).
That dataset is national-level only -- Germany doesn't publish a public,
regionally-broken-down hourly demand series -- so region-level allocation
needs *some* regional reference data to exist at all.

What's here:
  - REGIONS: Germany's 16 federal states (Bundesländer), each with its
    approximate 2019 population (public, Destatis-published figures) and
    an approximate lat/lon (its state capital, used as the region's
    centroid for distance calculations).
  - STATIONS: 8 real, geographically-spread major German generation sites
    (public knowledge -- these are well-known power stations), used here as
    *regional generation hubs* -- each one's `capacity_mw` represents the
    pooled dispatchable+renewable capacity reasonably reachable through that
    grid region, not that single named plant's own nameplate rating. Modeling
    all ~200+ GW of Germany's real, fragmented generation fleet as literal
    individual stations isn't practical for an 8-hub illustrative model, so
    each hub's capacity is scaled to keep national totals in a realistic
    range (~100 GW, comfortably above Germany's typical ~50-80 GW demand,
    matching real-world reserve margins) while keeping the named site as a
    recognizable geographic anchor for the region.

State populations and plant identities are real; capacities and exact
coordinates are approximate/illustrative (state-capital-as-centroid is a
simplification, not each state's true population centroid). This is
clearly a different tier of data quality than the committed OPSD dataset,
and is treated that way everywhere it's surfaced (labelled "reference
data", never presented as part of the verified time series).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    name: str
    population: int
    lat: float
    lon: float


@dataclass(frozen=True)
class Station:
    name: str
    lat: float
    lon: float
    capacity_mw: float


REGIONS: list[Region] = [
    Region("North Rhine-Westphalia", 17_932_651, 51.23, 6.77),
    Region("Bavaria", 13_124_737, 48.14, 11.58),
    Region("Baden-Württemberg", 11_100_394, 48.78, 9.18),
    Region("Lower Saxony", 7_993_608, 52.37, 9.73),
    Region("Hesse", 6_288_080, 50.08, 8.24),
    Region("Rhineland-Palatinate", 4_084_844, 49.99, 8.27),
    Region("Saxony", 4_071_971, 51.05, 13.74),
    Region("Berlin", 3_669_491, 52.52, 13.40),
    Region("Schleswig-Holstein", 2_903_773, 54.32, 10.14),
    Region("Brandenburg", 2_521_893, 52.40, 13.06),
    Region("Saxony-Anhalt", 2_194_782, 52.13, 11.64),
    Region("Thuringia", 2_133_378, 50.98, 11.03),
    Region("Hamburg", 1_847_253, 53.55, 9.99),
    Region("Mecklenburg-Vorpommern", 1_608_138, 53.63, 11.41),
    Region("Saarland", 986_887, 49.23, 7.00),
    Region("Bremen", 682_986, 53.08, 8.80),
]

STATIONS: list[Station] = [
    Station("Neurath hub (NRW)", 51.03, 6.66, 26_000.0),
    Station("Lippendorf hub (Saxony)", 51.19, 12.38, 9_000.0),
    Station("Staudinger hub (Hesse)", 50.09, 9.05, 8_000.0),
    Station("Rostock hub (Mecklenburg-Vorpommern)", 54.13, 12.13, 7_000.0),
    Station("Irsching hub (Bavaria)", 48.62, 11.68, 16_000.0),
    Station("Mannheim GKM hub (Baden-Württemberg)", 49.45, 8.54, 14_000.0),
    Station("Moorburg hub (Hamburg)", 53.48, 9.95, 10_000.0),
    Station("Brokdorf hub (Schleswig-Holstein)", 53.85, 9.35, 13_000.0),
]

TOTAL_POPULATION = sum(r.population for r in REGIONS)
