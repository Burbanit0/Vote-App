import React from 'react';
import { useTranslation } from 'react-i18next';
import { usePlaygroundCtx } from '../PlaygroundController';
import Collapsible from '../Collapsible';
import StrategicModule from '../StrategicModule';
import SincerityModule from '../SincerityModule';
import EquilibriumModule from '../EquilibriumModule';
import { useVotingLabels } from '../../../hooks/useVotingLabels';

// Moment ③ Stratégie & vote blanc — sincere vs tactical voting, manipulation,
// strategic desertion. The manipulation lens is foregrounded on the instrument.
const StrategyMoment: React.FC = () => {
  const { t } = useTranslation('playground');
  const { manipComplexity } = useVotingLabels();
  const {
    config,
    playground,
    setPlaygroundDeep,
    mode,
    assembly,
    leaderRule,
    leaderCandidates,
    votingVoters,
    dims,
    youPos,
    setYouPos,
    manipDetail,
  } = usePlaygroundCtx();

  if (mode !== 'leader') {
    return (
      <div className="flex flex-col gap-3 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('strategy.assemblyTitle')}
        </p>
        <label className="flex items-center gap-2 text-sm" title={t('strategy.duvergerTitle')}>
          <input
            data-testid="duverger-toggle"
            type="checkbox"
            checked={assembly.strategic_desertion}
            onChange={(e) => setPlaygroundDeep('assembly.strategic_desertion', e.target.checked)}
          />
          {t('strategy.duverger')}
        </label>
        <p className="text-[0.7rem] text-muted-foreground/80">{t('strategy.duvergerNote')}</p>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col gap-2 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('strategy.sincereTitle')}
        </p>
        <p className="text-[0.7rem] text-muted-foreground/80">{t('strategy.sincereHint')}</p>
        <SincerityModule
          voters={votingVoters}
          candidates={leaderCandidates}
          dims={dims}
          you={youPos}
          onYouChange={setYouPos}
        />
      </div>

      <Collapsible
        title={t('strategy.vulnTitle')}
        subtitle={t('strategy.vulnSub')}
        testid="module-strategic"
      >
        <StrategicModule config={config} playground={playground} />
      </Collapsible>

      <Collapsible
        title={t('strategy.equilibriumTitle')}
        subtitle={t('strategy.equilibriumSub')}
        testid="module-equilibrium"
      >
        <EquilibriumModule voters={votingVoters} candidates={leaderCandidates} />
      </Collapsible>

      {manipDetail && (
        <div
          data-testid="manip-hardness"
          className="rounded-md border border-border px-2.5 py-2 text-[0.7rem]"
        >
          <p className="font-semibold uppercase tracking-wide text-muted-foreground">
            {t('strategy.manipTitle')}
          </p>
          <p className="mt-1">
            {t('strategy.manipPrinciple')}{' '}
            <strong
              className={
                manipComplexity[leaderRule].hard
                  ? 'text-green-700 dark:text-green-400'
                  : 'text-amber-600 dark:text-amber-400'
              }
            >
              {manipComplexity[leaderRule].label}
            </strong>{' '}
            <span className="text-muted-foreground">({manipComplexity[leaderRule].ref})</span>
          </p>
          <p className="mt-0.5 text-muted-foreground">
            {t('strategy.probeIntro')}{' '}
            {manipDetail.probe.minCoalitionShare !== null
              ? t('strategy.probeCoalition', {
                  pct: Math.round(manipDetail.probe.minCoalitionShare * 100),
                })
              : t('strategy.probeNone')}
            {manipDetail.probe.backfired && t('strategy.probeBackfire')}.
          </p>
          <p className="mt-0.5 text-muted-foreground/80">
            {t('strategy.exampleIntro')}{' '}
            {manipDetail.easy.minCoalitionShare !== null
              ? t('strategy.examplePluralityOk', {
                  pct: Math.round(manipDetail.easy.minCoalitionShare * 100),
                })
              : t('strategy.examplePluralityFail')}
            {t('strategy.exampleIrvMid')}
            {manipDetail.hard.minCoalitionShare !== null
              ? t('strategy.exampleIrvDemands', {
                  pct: Math.round(manipDetail.hard.minCoalitionShare * 100),
                })
              : t('strategy.exampleIrvFail')}
            {manipDetail.hard.backfired ? t('strategy.exampleIrvBackfire') : ''}.
          </p>
        </div>
      )}
    </>
  );
};

export default StrategyMoment;
