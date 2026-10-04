import React from 'react';
import { useTranslation } from 'react-i18next';
import type { PolityRunSummary } from '../../hooks/usePolityData';
import { runName, unfinished } from '../../lib/polity/runs';
import { usePolityCtx } from './PolityController';

/** Which run the page shows, grouped by the root it was found in. */
const RunPicker: React.FC = () => {
  const { t } = useTranslation('polity');
  const { runs, runKey, setRunKey } = usePolityCtx();
  if (!runs || runs.length === 0) return null;

  const roots = new Map<string, PolityRunSummary[]>();
  for (const run of runs) roots.set(run.label, [...(roots.get(run.label) ?? []), run]);
  const label = (run: PolityRunSummary) => {
    const text = t('runPicker.option', {
      name: runName(run),
      population: run.population ?? '?',
      years: run.years ?? '?',
      seed: run.seed ?? '?',
      // A path's slashes would come out as &#x2F;. React escapes the option's text itself.
      interpolation: { escapeValue: false },
    });
    const progress = unfinished(run);
    return progress ? `${text} · ⚠ ${t('runFacts.unfinished', progress)}` : text;
  };
  const options = (members: PolityRunSummary[]) =>
    members.map((run) => (
      <option key={run.key} value={run.key}>
        {label(run)}
      </option>
    ));

  return (
    // Capped on the label, not only the select: as a flex item the label otherwise keeps the
    // width of the longest option. And clipped horizontally: WebKit adds an option wider than
    // its <select> to the page's scrollable width even though the select stays inside, so
    // /polity scrolled sideways in longer languages. The clip margin keeps the select's focus
    // outline visible where overflow-clip-margin is supported.
    <label
      className="flex min-w-0 max-w-[min(28rem,100%)] flex-col gap-1 overflow-x-clip text-sm [overflow-clip-margin:4px]"
      htmlFor="polity-run-picker"
    >
      <span className="font-mono text-[0.66rem] uppercase tracking-[0.18em] text-muted-foreground">
        {t('runPicker.label')}
      </span>
      <select
        id="polity-run-picker"
        data-testid="polity-run-picker"
        className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
        // A listed run is always picked (pickRun falls back to the first), so the key is set here.
        value={runKey as string}
        onChange={(e) => setRunKey(e.target.value)}
      >
        {/* One root needs no group header. */}
        {roots.size > 1
          ? [...roots].map(([root, members]) => (
              <optgroup key={root} label={root}>
                {options(members)}
              </optgroup>
            ))
          : options(runs)}
      </select>
    </label>
  );
};

export default RunPicker;
