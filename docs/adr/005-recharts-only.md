# ADR 005 — Recharts as the only chart library

**Status:** Accepted (Phase 6, 2026-06)

## Context

The frontend bundled three charting stacks: chart.js + react-chartjs-2,
react-google-charts, and Recharts, plus D3 — roughly 700 KB of overlapping
capability.

## Decision

Standardise on **Recharts** for declarative charts and keep **D3** only for the
bespoke geometry it is uniquely good at (Voronoi regions via d3-delaunay, hexbin,
force-directed method-similarity graph). chart.js, react-chartjs-2, and
react-google-charts were removed.

## Consequences

- ~700 KB smaller bundle; one charting mental model.
- Recharts composes as React components, matching the rest of the codebase.
- The few genuinely custom visualisations (ideology map, heatmap, hemicycles) are
  hand-rolled SVG + D3 math, not a chart library — that was always the right tool.
