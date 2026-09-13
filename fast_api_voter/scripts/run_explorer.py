"""Polity run explorer (S5.2): browse every run on disk -- the registry, runs of one shape
across seeds, one run tick by tick, its presidency term by term, and any citizen's
biography. The data comes from api/domain/polity/run_explorer.py; this file is widgets.

Usage (from fast_api_voter/):
    marimo run scripts/run_explorer.py        # as an app
    marimo edit scripts/run_explorer.py       # as an editable notebook

Extra run roots beyond scripts/*_runs (the p500 batch's worktree, say), colon-separated:
    POLITY_RUN_ROOTS=../../Vote-App-p500/fast_api_voter/scripts/seed_sweep_runs marimo run scripts/run_explorer.py
POLITY_EXPLORER_RUN=<run dir> opens that run first.
"""
import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full", app_title="Polity run explorer")


@app.cell
def _():
    import os
    import sys
    from pathlib import Path

    import marimo as mo

    backend = Path(mo.notebook_dir()).resolve().parent
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

    from api.domain.polity.run_explorer import (
        RunView,
        citizen_biography,
        citizen_census,
        cross_seed_rows,
        run_choices,
        term_rows,
        tick_summary,
    )
    from api.domain.polity.run_registry import build_registry

    return (
        Path, RunView, backend, build_registry, citizen_biography, citizen_census, cross_seed_rows, mo, os,
        run_choices, term_rows, tick_summary,
    )


@app.cell
def _(Path, backend, build_registry, mo, os):
    extra_roots = [Path(root) for root in os.environ.get("POLITY_RUN_ROOTS", "").split(":") if root]
    roots = sorted((backend / "scripts").glob("*_runs")) + extra_roots
    registry = build_registry(roots)
    runs_table = registry.execute(
        "SELECT run_id, generation, outcome, engine, population, years, seed, ticks_reached, ticks_planned, "
        "round(office_occupancy, 3) AS occupancy, fallbacks, round(elapsed_seconds / 3600, 2) AS hours "
        "FROM runs ORDER BY run_dir"
    )
    columns = [column[0] for column in runs_table.description]
    mo.vstack([
        mo.md(f"# Polity runs\n{len(roots)} run roots scanned"),
        mo.ui.table([dict(zip(columns, row)) for row in runs_table.fetchall()], selection=None),
    ])
    return (registry,)


@app.cell
def _(cross_seed_rows, mo, registry):
    mo.vstack([
        mo.md("## Same shape, different seeds (completed runs)"),
        mo.ui.table(cross_seed_rows(registry), selection=None),
    ])
    return


@app.cell
def _(mo, os, registry, run_choices):
    choices = run_choices(registry)
    preselected = next((label for label, run_dir in choices.items() if run_dir == os.environ.get("POLITY_EXPLORER_RUN")), None)
    picker = mo.ui.dropdown(options=choices, value=preselected, label="Run", searchable=True, full_width=True)
    picker
    return (picker,)


@app.cell
def _(Path, RunView, mo, picker, term_rows):
    mo.stop(picker.value is None, mo.md("*Pick a run to explore it.*"))
    view = RunView.load(Path(picker.value))
    mo.vstack([
        mo.md(f"## {view.run_id}\n{len(view.events)} events, ticks 0-{view.last_tick} of {view.ticks_planned}"),
        mo.md("### The presidency, term by term"),
        mo.ui.table(term_rows(view), selection=None),
    ])
    return (view,)


@app.cell
def _(mo, view):
    tick_slider = mo.ui.slider(0, view.last_tick, value=0, label="Tick", show_value=True, full_width=True)
    tick_slider
    return (tick_slider,)


@app.cell
def _(mo, tick_slider, tick_summary, view):
    summary = tick_summary(view, tick_slider.value)
    mo.vstack([
        mo.md(
            f"### Tick {summary['tick']} (year {summary['tick'] // 4})\n"
            f"President: **{summary['president']}** · legitimacy {summary['legitimacy']} · "
            f"{summary['llm_decisions']} model decisions, {summary['llm_fallbacks']} fallbacks"
        ),
        mo.ui.table(summary["institutional"], selection=None) if summary["institutional"] else mo.md("*No institutional event this tick.*"),
        mo.ui.table([{"event_type": k, "count": v} for k, v in summary["events"].items()], selection=None),
    ])
    return


@app.cell
def _(mo, view):
    citizen = mo.ui.number(start=0, stop=max((e.get("citizen_id") or 0) for e in view.events), value=view.terms[0].holder_id if view.terms else 0, label="Citizen")
    citizen
    return (citizen,)


@app.cell
def _(citizen, citizen_biography, citizen_census, mo, view):
    biography = citizen_biography(view, int(citizen.value))
    mo.vstack([
        mo.md(f"### Citizen {int(citizen.value)}: {len(biography)} events"),
        mo.ui.table(citizen_census(view, int(citizen.value)), selection=None),
        mo.ui.table(biography, selection=None, page_size=15),
    ])
    return


if __name__ == "__main__":
    app.run()
