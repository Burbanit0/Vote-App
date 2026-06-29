import React from 'react';
import { useTranslation } from 'react-i18next';
import { usePlaygroundCtx } from '../PlaygroundController';
import { Field, selectCls } from '../playgroundFields';
import { useVotingLabels } from '../../../hooks/useVotingLabels';

const StrategyMoment: React.FC = () => {
  const { t } = useTranslation('playground');
  const { manipComplexity } = useVotingLabels();
  const {
    setPlayground,
    setPlaygroundDeep,
    mode,
    assembly,
    leaderRule,
    voters,
    votingVoters,
    turnout,
    behavior,
    manipDetail,
  } = usePlaygroundCtx();

  return (
    <>
      {/* ── Behavior (absorbed from Électorat) ── */}
      <Field label={t('electorate.behaviorLabel')} htmlFor="pg-behavior">
        <select
          id="pg-behavior"
          className={selectCls}
          value={behavior}
          onChange={(e) => setPlayground({ behavior: e.target.value as typeof behavior })}
        >
          <option value="sincere">{t('electorate.behaviorSincere')}</option>
          <option value="strategic">{t('electorate.behaviorStrategic')}</option>
          <option value="mixed">{t('electorate.behaviorMixed')}</option>
        </select>
      </Field>

      {/* ── Participation (absorbed from Électorat) ── */}
      <div className="flex flex-col gap-2 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('electorate.participationTitle')}
        </p>
        <Field label={t('electorate.abstentionModelLabel')} htmlFor="pg-turnout">
          <select
            id="pg-turnout"
            data-testid="turnout-select"
            className={selectCls}
            value={turnout.model}
            onChange={(e) => setPlaygroundDeep('turnout.model', e.target.value)}
          >
            <option value="full">{t('electorate.abstentionFull')}</option>
            <option value="alienation">{t('electorate.abstentionAlienation')}</option>
            <option value="indifference">{t('electorate.abstentionIndifference')}</option>
          </select>
        </Field>
        {turnout.model !== 'full' && (
          <>
            <Field
              label={t('electorate.intensity', { pct: Math.round(turnout.intensity * 100) })}
              htmlFor="pg-turnout-int"
            >
              <input
                id="pg-turnout-int"
                data-testid="turnout-intensity"
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={turnout.intensity}
                onChange={(e) => setPlaygroundDeep('turnout.intensity', Number(e.target.value))}
              />
            </Field>
            {mode === 'leader' && (
              <p data-testid="turnout-rate" className="text-[0.7rem] text-muted-foreground">
                {t('electorate.turnoutLabel')}{' '}
                <strong>
                  {Math.round((votingVoters.length / Math.max(1, voters.length)) * 100)} %
                </strong>{' '}
                {t('electorate.turnoutAbstentions', {
                  count: voters.length - votingVoters.length,
                })}
              </p>
            )}
          </>
        )}
      </div>

      {/* ── Assembly strategic desertion (parliament mode) ── */}
      {mode === 'parliament' && (
        <div className="flex flex-col gap-2 rounded-md border border-border p-3">
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
      )}

      {/* ── Vote utile: manipulation hardness (leader mode) ── */}
      {mode === 'leader' && manipDetail && (
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
