import React from 'react';
import { useTranslation } from 'react-i18next';
import { TallyLoader } from '@/components/ui/tally';
import { RiseWords } from '@/components/ui/slip';
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
}) =>
  busy ? (
    <TallyLoader data-testid={testId} className="justify-start py-6" label={children} />
  ) : (
    <p
      data-testid={testId}
      role="alert"
      className="flex items-center gap-2 py-6 text-sm text-muted-foreground"
    >
      {children}
    </p>
  );

/** A block of the run view, coming in after the one above it, as the homepage's sections do. */
const Rise: React.FC<{ at: number; className?: string; children: React.ReactNode }> = ({
  at,
  className,
  children,
}) => (
  <div className={`home-up ${className ?? ''}`} style={{ animationDelay: `${at * 80}ms` }}>
    {children}
  </div>
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
    <div className="flex flex-col gap-6">
      <Rise at={0}>
        <RunFacts />
      </Rise>
      <Rise at={1}>
        <TickPlayer />
      </Rise>
      <Rise at={2}>
        <InstitutionalTimeline />
      </Rise>
      {/* On a wide screen the selected citizen's story sits beside the map, in a column of its
          own that stays in view and scrolls by itself; it is always there, so selecting
          someone never resizes the map. */}
      <Rise at={3} className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <PopulationMap />
        <div className="lg:sticky lg:top-14 lg:max-h-[calc(100vh-4.5rem)] lg:overflow-y-auto">
          {/* A citizen is only read from the URL once a run is shown, so the run key is set here. */}
          {citizen !== null ? (
            <CitizenBiographyPanel runKey={runKey as string} citizen={citizen} />
          ) : (
            <p
              data-testid="polity-biography-hint"
              className="rounded-2xl border border-dashed border-border px-4 py-4 text-sm text-muted-foreground"
            >
              {t('biography.hint')}
            </p>
          )}
        </div>
      </Rise>
      <Rise at={4}>
        <MacroCurves />
      </Rise>
    </div>
  );
};

const PolityShell: React.FC = () => {
  const { t } = useTranslation('polity');
  return (
    <div
      data-testid="polity-page"
      className="mx-auto w-full max-w-[1600px] px-4 pt-12 pb-16 sm:px-6"
    >
      <header className="mb-8 flex flex-wrap items-end justify-between gap-x-10 gap-y-5">
        <div className="flex max-w-3xl flex-col gap-4">
          <p className="home-up text-[15px] font-bold text-primary">{t('masthead.kicker')}</p>
          <h1 className="font-display text-[clamp(48px,5.6vw,88px)] leading-[0.9] font-extrabold">
            <RiseWords text={t('masthead.title')} delay={80} />
          </h1>
          <p className="home-up text-lg text-muted-foreground" style={{ animationDelay: '200ms' }}>
            {t('masthead.subtitle')}
          </p>
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
