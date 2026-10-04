import React from 'react';
import { useTranslation } from 'react-i18next';
import { Spinner } from '@/components/ui/spinner';
import { PolityProvider, usePolityCtx } from '../components/polity/PolityController';
import RunPicker from '../components/polity/RunPicker';
import RunFacts from '../components/polity/RunFacts';
import { messageOf } from '../lib/polity/errors';
import TickPlayer from '../components/polity/TickPlayer';
import InstitutionalTimeline from '../components/polity/InstitutionalTimeline';
import PopulationMap from '../components/polity/PopulationMap';
import MacroCurves from '../components/polity/MacroCurves';
import CitizenBiographyPanel from '../components/polity/CitizenBiographyPanel';

// The run explorer: a finished polity simulation replayed tick by tick. The page
// is a layout shell over PolityController; each view (player, map, curves,
// biography) is a thin consumer of its context.

const Status: React.FC<{ testId: string; children: React.ReactNode; busy?: boolean }> = ({
  testId,
  children,
  busy = false,
}) => (
  <p
    data-testid={testId}
    role={busy ? 'status' : 'alert'}
    className="flex items-center gap-2 py-6 text-sm text-muted-foreground"
  >
    {busy && <Spinner size="sm" />}
    {children}
  </p>
);

const PolityBody: React.FC = () => {
  const { t } = useTranslation('polity');
  const {
    runs,
    runsLoading,
    runsError,
    runKey,
    overview,
    overviewLoading,
    overviewError,
    citizen,
  } = usePolityCtx();

  if (runsLoading)
    return (
      <Status testId="polity-runs-loading" busy>
        {t('runStates.loadingRuns')}
      </Status>
    );
  if (runsError) {
    return (
      <Status testId="polity-runs-error">
        {t('runStates.runsError', { message: messageOf(runsError) })}
      </Status>
    );
  }
  if (!runs || runs.length === 0)
    return <Status testId="polity-no-runs">{t('runStates.noRuns')}</Status>;
  if (overviewError) {
    return (
      <Status testId="polity-run-error">
        {t('runStates.runError', { message: messageOf(overviewError) })}
      </Status>
    );
  }
  if (overviewLoading || !overview) {
    return (
      <Status testId="polity-run-loading" busy>
        {t('runStates.loadingRun')}
      </Status>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <RunFacts />
      <TickPlayer />
      <InstitutionalTimeline />
      {/* On a wide screen the selected citizen's story sits beside the map, in a column of its
          own that stays in view and scrolls by itself; it is always there, so selecting
          someone never resizes the map. */}
      <div className="grid items-start gap-3 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <PopulationMap />
        <div className="lg:sticky lg:top-14 lg:max-h-[calc(100vh-4.5rem)] lg:overflow-y-auto">
          {/* A citizen is only read from the URL once a run is shown, so the run key is set here. */}
          {citizen !== null ? (
            <CitizenBiographyPanel runKey={runKey as string} citizen={citizen} />
          ) : (
            <p
              data-testid="polity-biography-hint"
              className="rounded-md border border-dashed border-border px-3 py-2 text-xs text-muted-foreground"
            >
              {t('biography.hint')}
            </p>
          )}
        </div>
      </div>
      <MacroCurves />
    </div>
  );
};

const PolityShell: React.FC = () => {
  const { t } = useTranslation('polity');
  return (
    <div data-testid="polity-page" className="w-full px-4 py-4">
      <header className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b border-border pb-3">
        <div>
          <p className="font-mono text-[0.66rem] uppercase tracking-[0.22em] text-primary">
            {t('masthead.kicker')}
          </p>
          <h1 className="mt-0.5 font-display text-2xl font-bold tracking-tight sm:text-3xl">
            {t('masthead.title')}
          </h1>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">{t('masthead.subtitle')}</p>
        </div>
        <RunPicker />
      </header>
      <PolityBody />
    </div>
  );
};

const PolityPage: React.FC = () => (
  <PolityProvider>
    <PolityShell />
  </PolityProvider>
);

export default PolityPage;
