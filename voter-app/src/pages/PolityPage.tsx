import React from 'react';
import { useTranslation } from 'react-i18next';
import { Spinner } from '@/components/ui/spinner';
import { PolityProvider, usePolityCtx } from '../components/polity/PolityController';
import RunPicker from '../components/polity/RunPicker';
import RunFacts from '../components/polity/RunFacts';

// The run explorer: a finished polity simulation replayed tick by tick. The page
// is a layout shell over PolityController; each view (player, map, curves,
// biography) is a thin consumer of its context.

/** The API's error body carries `detail`; anything else is shown as text. */
function messageOf(error: unknown): string {
  if (error && typeof error === 'object' && 'detail' in error) return String(error.detail);
  return String(error);
}

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
  const { runs, runsLoading, runsError, overview, overviewLoading, overviewError } = usePolityCtx();

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
  return <RunFacts />;
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
