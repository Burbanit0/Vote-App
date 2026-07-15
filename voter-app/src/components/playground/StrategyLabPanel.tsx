import React from 'react';
import { useTranslation } from 'react-i18next';
import { usePlaygroundCtx } from './PlaygroundController';
import SincerityModule from './SincerityModule';
import StrategicModule from './StrategicModule';
import EquilibriumModule from './EquilibriumModule';
import VseModule from './VseModule';
import Collapsible from './Collapsible';
import { AnchorFallback } from './playgroundFields';

const AbstentionPanel = React.lazy(() => import('../shared/AbstentionPanel'));

const StrategyLabPanel: React.FC = () => {
  const { t } = useTranslation('playground');
  const {
    config,
    playground,
    mode,
    dims,
    votingVoters,
    leaderCandidates,
    youPos,
    setYouPos,
    sampleAtSeed,
    baseSeed,
  } = usePlaygroundCtx();

  if (mode !== 'leader') {
    return <p className="text-xs text-muted-foreground">{t('strategy.leaderOnly')}</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('strategy.sincereTitle')}
        </p>
        <SincerityModule
          voters={votingVoters}
          candidates={leaderCandidates}
          dims={dims}
          you={youPos}
          onYouChange={setYouPos}
        />
      </div>

      <div className="flex flex-col gap-2 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('strategy.vulnTitle')}
        </p>
        <StrategicModule config={config} playground={playground} />
      </div>

      <div className="flex flex-col gap-2 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('strategy.equilibriumTitle')}
        </p>
        <EquilibriumModule voters={votingVoters} candidates={leaderCandidates} />
      </div>

      {/* The welfare cost of strategy (VSE). Collapsed: the sweep is a Monte-Carlo
          over every method × strategic share, so it must not run until asked for. */}
      <Collapsible title={t('vse.title')} subtitle={t('vse.subtitle')} testid="anchor-vse">
        <VseModule sampleAtSeed={sampleAtSeed} baseSeed={baseSeed} candidates={leaderCandidates} />
      </Collapsible>

      <Collapsible
        title={t('electorate.abstentionAnchorTitle')}
        subtitle={t('electorate.abstentionAnchorSub')}
        testid="anchor-abstention"
      >
        <React.Suspense fallback={<AnchorFallback />}>
          <AbstentionPanel />
        </React.Suspense>
      </Collapsible>
    </div>
  );
};

export default StrategyLabPanel;
