import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { usePlaygroundCtx } from '../PlaygroundController';
import { Field, selectCls, AnchorFallback } from '../playgroundFields';
import Collapsible from '../Collapsible';
import ScenarioInfo from '../ScenarioInfo';
import ElectorateComposer from '../ElectorateComposer';

const AbstentionPanel = React.lazy(() => import('../../shared/AbstentionPanel'));

// Moment ① Électorat — who votes, how they cluster and behave.
const ElectorateMoment: React.FC = () => {
  const { t } = useTranslation('playground');
  const {
    config,
    setPlayground,
    setPlaygroundDeep,
    applyPreset,
    presets,
    mode,
    space,
    behavior,
    prefSource,
    turnout,
    composed,
    electorate,
    voters,
    votingVoters,
  } = usePlaygroundCtx();
  const pointWord = mode === 'leader' ? t('common.candidates') : t('common.parties');

  return (
    <>
      <Collapsible
        title={t('electorate.composeTitle')}
        subtitle={
          composed
            ? t('electorate.composeSubComposed', { count: electorate.communities.length })
            : t('electorate.composeSubSimple')
        }
        testid="module-electorate"
      >
        <ElectorateComposer />
      </Collapsible>

      <Field label={t('electorate.startLabel')}>
        <div className="flex flex-col gap-1.5">
          {presets.map((p) => (
            <div key={p.id} className="flex items-center gap-1">
              <button
                data-testid={`preset-${p.id}`}
                type="button"
                onClick={() => applyPreset(p.id)}
                className={cn(
                  'flex-1 rounded-md border border-border px-2.5 py-1.5 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground'
                )}
                title={t(`presets.${p.id}.desc`, { defaultValue: p.description })}
              >
                {t(`presets.${p.id}.label`, { defaultValue: p.label })}
              </button>
              <ScenarioInfo scenario={p.id} />
            </div>
          ))}
        </div>
      </Field>

      <div className="rounded-md bg-muted/40 px-2.5 py-2 text-xs text-muted-foreground">
        {t('electorate.summary', {
          points: config.candidates.length,
          pointWord,
          voters: config.num_voters,
          ideology: config.ideology,
        })}
      </div>

      <Field label={t('electorate.dimsLabel')} htmlFor="pg-dims">
        <select
          id="pg-dims"
          className={selectCls}
          value={space.dims}
          onChange={(e) => setPlaygroundDeep('space.dims', Number(e.target.value))}
        >
          <option value={1}>{t('electorate.dims1')}</option>
          <option value={2}>{t('electorate.dims2')}</option>
          <option value={3}>{t('electorate.dims3')}</option>
        </select>
      </Field>

      <Field label={t('electorate.sourceLabel')} htmlFor="pg-source">
        <select
          id="pg-source"
          className={selectCls}
          value={prefSource}
          onChange={(e) => setPlayground({ prefSource: e.target.value as typeof prefSource })}
        >
          <option value="spatial">{t('electorate.sourceSpatial')}</option>
          <option value="impartial">{t('electorate.sourceImpartial')}</option>
          <option value="mallows">{t('electorate.sourceMallows')}</option>
          <option value="urn">{t('electorate.sourceUrn')}</option>
          <option value="handcrafted">{t('electorate.sourceHandcrafted')}</option>
        </select>
      </Field>

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

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={space.valenceEnabled}
          onChange={(e) => setPlaygroundDeep('space.valenceEnabled', e.target.checked)}
        />
        {t('electorate.valence')}
      </label>

      {/* ── Participation / abstention (réalisme électoral) ── */}
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
        <p className="text-[0.65rem] text-muted-foreground">{t('electorate.downsNote')}</p>
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
    </>
  );
};

export default ElectorateMoment;
