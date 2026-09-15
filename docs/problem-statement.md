# Problem Statement

## U2: Grid Load Optimisation & Renewable Energy

The US curtailed roughly 8 TWh of clean energy in 2023 -- solar and wind
generation switched off not because the sun stopped shining or the wind
stopped blowing, but because the grid couldn't absorb it in the moment it
was produced. At the same time, unexpected demand spikes strain grid
stability from the other direction: operators have to keep supply and
demand balanced within seconds, with no room to "catch up" later.

Both problems land on the same desk. A grid operator has to simultaneously:

- **forecast** where demand is heading, and flag when it's about to spike
  beyond what was planned for;
- **watch renewable assets** (solar farms, onshore and offshore wind) for
  underperformance, and figure out *why* -- a bad weather day, a genuine
  equipment fault, or a curtailment order that already happened -- because
  each of those calls for a different response;
- **decide, hour by hour,** how to use dispatchable generation, battery
  storage, and demand response to keep the grid balanced without wasting
  clean energy; and
- **turn all of that into an actionable brief** a shift operator can read
  in two minutes, not a spreadsheet they have to reverse-engineer.

Today this is done with fragmented tooling and a lot of manual
cross-referencing under time pressure. GridSentinel builds one pipeline
that does the forecasting, the anomaly detection, the root-causing, and the
optimisation in sequence, and hands the operator a single verified brief at
the end of it.
