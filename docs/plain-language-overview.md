# GridSentinel — Explained in Plain Language

This is the "explain it to someone who isn't a programmer" version of the project.
If you want the technical version instead, read `docs/PROJECT_OVERVIEW.md`. This one
skips the jargon and just walks through what the thing does, why, and how it got built.

---

## 1. What problem are we solving?

Electricity grids have two opposite problems happening at the same time:

- **Sometimes there's too much demand.** People turn on ACs, EVs charge, factories
  run — and if the grid didn't see the spike coming, that's a real risk (brownouts,
  emergency dispatch, expensive last-minute power buying).
- **Sometimes there's too much clean energy and nowhere for it to go.** Solar and
  wind farms generate more power than the grid can use or store at that moment, so
  operators are forced to *switch them off* — this is called **curtailment**, and it's
  wasted clean energy. In 2023 the US alone curtailed about 8 TWh of renewable power
  this way.

Right now, the people whose job is to watch for both of these problems (grid
operators) mostly do it by hand: checking dashboards, spreadsheets, gut feeling,
under time pressure. GridSentinel is a tool that does this watching automatically.

---

## 2. What does GridSentinel actually do?

Think of it like a very thorough assistant who, every time you ask, does all of this
in about a minute:

1. **"How much electricity will people need over the next day?"** — looks at the
   normal weekly pattern (Mondays look like Mondays, evenings look like evenings) and
   flags any hour where demand looks like it's about to spike higher than usual.
2. **"Is the solar and wind actually producing what it should be?"** — compares what
   each solar farm / wind farm *should* be generating (based on weather-normal
   expectations) against what it's *actually* generating, and flags any asset that's
   been sustainedly underperforming — not just one noisy bad hour, but a real,
   ongoing dip.
3. **"Why is it underperforming?"** — for every flagged dip, it works out the most
   likely reason: is this curtailment (there's more power than the grid needs right
   now), bad weather, a broken/offline piece of equipment, or is it actually just a
   *good* surprise (more power than expected, not a problem at all)?
4. **"What should we actually do about it, hour by hour?"** — works out the cheapest
   valid plan to meet demand: how much to draw from the grid, how much to charge or
   discharge from batteries, and whether to ask big users to cut back temporarily
   (demand response).
5. **"How much clean energy does that plan actually save?"** — compares that plan
   against what would have happened with *no* flexibility at all (no batteries, no
   demand response), and reports the real difference in megawatt-hours of clean
   energy that stayed on the grid instead of being wasted.
6. **"Write that up for a human to read."** — turns all those numbers into a short,
   readable brief, like a shift-handover report.
7. **"Now double-check every number in that report."** — before anything is shown to
   a person, a separate checking step re-reads the report, pulls out every number it
   claims, and verifies each one against the actual math from steps 1–5. If the
   write-up ever says a number that doesn't match reality, this step catches it and
   flags it — so nobody makes a real decision off a made-up figure.

That seven-step sequence is "the pipeline." It runs as one connected chain — each
step feeds the next — and the dashboard shows you it happening live, step by step, as
it runs.

---

## 3. Why does step 7 (double-checking) matter so much?

Because step 6 is the one place in the whole system where something resembling
"AI creative writing" happens — a report needs to describe numbers in plain
sentences, not just print a spreadsheet. Anywhere text gets generated, there's a
risk of it getting a number slightly wrong or making something up. So the team
built a rule into the whole system: **the writing step is only ever allowed to
describe numbers that were already calculated by ordinary, tested, deterministic
code — it's never allowed to calculate anything itself.** And then, on top of
that rule, a completely separate check re-verifies it actually followed the rule
before a human ever sees the report. There's even a test that deliberately makes
the write-up lie about a number, just to prove the checker catches it.

This is the part of the project the team is proudest of — it's what makes the
output something you could actually hand to a grid operator making a real
decision, instead of "an AI said so, trust it."

---

## 4. What can you actually see and click?

A web dashboard with these screens:

- **Command Center** — the home screen: quick status, a recent run's key numbers
  (peak demand, renewable output, how much curtailment was avoided, whether the
  last report passed its own fact-check), and a shortcut to start a new run.
- **New Run** — pick a time window, hit run, and watch the pipeline execute live
  (a progress feed shows each of the 7 steps completing in real time).
- **Anomaly Intelligence** — the list of flagged solar/wind dips, with the
  system's best guess at *why* each one happened.
- **Optimization Plan** — the hour-by-hour dispatch/battery/demand-response plan,
  plus an animated diagram showing energy actually flowing from sun → panels →
  inverter → battery / home / grid for whichever hour you're looking at (you can
  scrub through the hours like a timeline slider).
- **Curtailment Impact** — how much clean energy the plan saved compared to doing
  nothing extra.
- **Operator Brief** — the human-readable write-up, plus a "Verified" or
  "Flagged" badge showing whether the fact-check passed, and a one-click PDF
  export.
- **Run History** — every past run, so nothing is thrown away.

The whole dashboard supports both a dark theme and a light theme (there's a toggle
in the top bar), and it remembers whichever one you picked.

---

## 5. How was it actually built, in order?

1. **Figure out exactly what the problem is.** Before writing any code, the team
   wrote down precisely what a grid operator needs to know and decide, so the
   project had a clear target instead of a vague idea.
2. **Get real data, not made-up data.** Rather than fabricate sample numbers, the
   team used a real public dataset: actual hourly electricity demand and solar/wind
   generation for Germany, 2017–2019, sourced from an official European grid-data
   archive. Using real data means the numbers the system produces are trustworthy,
   not just plausible-looking.
3. **Build and test each calculation on its own first.** Demand forecasting, dip
   detection, root-cause guessing, the dispatch-planning math, and the
   curtailment-savings math were each written and tested *separately*, before any
   of them were connected together — so each piece was proven correct in isolation.
4. **Chain them together into one pipeline.** Once each calculation worked on its
   own, they were wired into the single connected 7-step sequence described above,
   so a single button press runs the whole thing end-to-end and streams its
   progress live.
5. **Add the write-up step, then the fact-checking step.** First the plain-English
   report generator, then — deliberately as a *separate* piece — the checker that
   verifies the report against the real numbers.
6. **Expose it over the web.** Built the backend server so a website can trigger a
   run, watch it live, fetch the finished result, and download a PDF of it.
7. **Build the dashboard.** A full web interface: the run form, the live progress
   view, the charts, tables, and report pages listed in section 4.
8. **Test everything.** Grew a large automated test suite (currently 50 tests)
   covering every calculation and the pipeline as a whole, so future changes can't
   silently break something that used to work.
9. **Polish the dashboard.** Most recently: added a light/dark theme switch, fixed
   the backend-connection status indicator, gave every button/click a real,
   working action, added smooth page-transition and hover animations, redesigned
   the color scheme, made the top navigation bar bigger and cleaner, added an
   animated "energy flow" diagram to the Optimization Plan page showing power
   moving from sun → panels → inverter → battery/home/grid for any hour you pick,
   and added an animated, auto-playing hero banner to the Command Center home
   screen that visually explains the pipeline (forecast → detect → optimize →
   verify), the solar-to-grid flow, and the curtailment-savings story — each as
   its own labeled diagram that recolors correctly in both themes.
10. **Write it all up.** Documentation, a test report, demo screenshots, and this
    plain-language explainer.

---

## 6. What's *not* finished / what to know before relying on it

Being upfront about the current limits:

- **The dataset is real, but it's one country over one three-year window**
  (Germany, 2017–2019) — not a live, worldwide, real-time feed.
- **Curtailment shows up as close to zero most of the time in this specific
  dataset**, because Germany rarely had more renewable power than demand during
  those exact years at the national level. That's not a bug — the savings math is
  tested and proven correct against situations that *do* have oversupply, and it
  will report real, non-zero savings automatically on any time window (or future
  dataset) where supply gets close to or exceeds demand.
- **The optional AI-narration path (IBM watsonx.ai) is real, working code, but
  wasn't actually turned on in this build** — no API key was available in the dev
  environment, so the default, fully-offline template writer is what actually
  produced every report you'll see. Nothing about the *trustworthiness* changes
  either way, since the fact-checking step verifies whichever writer ran.
- **Run history is stored in memory on the server**, not a permanent database —
  fine for a demo, but it would need a real database to survive a server restart
  or serve multiple people reliably in production.
- **Battery size and dispatch limits currently default automatically** from each
  time window's peak demand; there isn't yet a dashboard control to type in custom
  values, even though the backend already accepts them.

---

## 7. Who worked on it

| Role | Name |
|---|---|
| Team Name | CodeCatalyst |
| Track | AI Utilities |
| Team Lead | Heer Pathak |
| Members | Manasvee Viroja, Priyal Kalariya, Prince Patel |

---

## 8. Where to look next

- Technical deep-dive: `docs/PROJECT_OVERVIEW.md`
- The original problem write-up: `docs/problem-statement.md`
- How the pieces fit together under the hood: `docs/architecture.md`
- How to run it yourself: `docs/setup-guide.md`
- Proof it actually works: `TEST_REPORT.md`
