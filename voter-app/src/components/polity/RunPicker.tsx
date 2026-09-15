import React from 'react';
import { useTranslation } from 'react-i18next';
import { usePolityCtx } from './PolityController';

/** Which finished run the page shows. */
const RunPicker: React.FC = () => {
  const { t } = useTranslation('polity');
  const { runs, runKey, setRunKey } = usePolityCtx();
  if (!runs || runs.length === 0) return null;

  return (
    // Capped on the label, not only the select: as a flex item the label otherwise keeps the
    // width of the longest option, which a longer language pushes past the page (WebKit).
    <label
      className="flex min-w-0 max-w-[min(28rem,100%)] flex-col gap-1 text-sm"
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
        {runs.map((run) => (
          <option key={run.key} value={run.key}>
            {t('runPicker.option', {
              runId: run.run_id,
              population: run.population ?? '?',
              years: run.years ?? '?',
              seed: run.seed ?? '?',
            })}
          </option>
        ))}
      </select>
    </label>
  );
};

export default RunPicker;
