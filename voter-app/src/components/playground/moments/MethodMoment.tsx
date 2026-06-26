import React from 'react';
import { useTranslation } from 'react-i18next';
import { usePlaygroundCtx } from '../PlaygroundController';
import { Field, selectCls, AnchorFallback } from '../playgroundFields';
import Collapsible from '../Collapsible';

const BlankVoteDivergencePanel = React.lazy(() => import('../../shared/BlankVoteDivergencePanel'));

const BALLOT_TYPES = [
  'full',
  'choose_one',
  'approve',
  'rank_full',
  'rank_truncated',
  'score',
  'grade',
  'cumulative',
] as const;

// Moment ② Méthode & bulletin — what the ballot can say + how the assembly counts.
// The counting rule and the map's lens are chosen on the instrument itself.
const MethodMoment: React.FC = () => {
  const { t } = useTranslation('playground');
  const { config, playground, setPlaygroundDeep, mode, assembly, result } = usePlaygroundCtx();

  return (
    <>
      <p className="text-xs text-muted-foreground">{t('method.note')}</p>

      <div className="flex flex-col gap-2 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('method.ballotTitle')}
        </p>
        <Field label={t('method.ballotTypeLabel')} htmlFor="pg-ballot">
          <select
            id="pg-ballot"
            data-testid="ballot-select"
            className={selectCls}
            value={playground.ballot.type}
            onChange={(e) => setPlaygroundDeep('ballot.type', e.target.value)}
          >
            {BALLOT_TYPES.map((k) => (
              <option key={k} value={k}>
                {t(`method.ballot.${k}`)}
              </option>
            ))}
          </select>
        </Field>
        {playground.ballot.type === 'rank_truncated' && (
          <Field
            label={t('method.truncateLabel', { n: playground.ballot.truncate_at })}
            htmlFor="pg-truncate"
          >
            <input
              id="pg-truncate"
              data-testid="ballot-truncate"
              type="range"
              min={1}
              max={Math.max(1, config.candidates.length)}
              step={1}
              value={playground.ballot.truncate_at}
              onChange={(e) => setPlaygroundDeep('ballot.truncate_at', Number(e.target.value))}
            />
          </Field>
        )}
        {(playground.ballot.type === 'score' || playground.ballot.type === 'grade') && (
          <Field
            label={t('method.levelsLabel', {
              n: playground.ballot.type === 'grade' ? 7 : playground.ballot.score_levels,
            })}
            htmlFor="pg-levels"
          >
            <input
              id="pg-levels"
              type="range"
              min={2}
              max={10}
              step={1}
              value={playground.ballot.score_levels}
              disabled={playground.ballot.type === 'grade'}
              onChange={(e) => setPlaygroundDeep('ballot.score_levels', Number(e.target.value))}
            />
          </Field>
        )}

        {result && (
          <div
            data-testid="ballot-preview"
            className="rounded bg-muted/40 px-2 py-1.5 text-[0.7rem] text-muted-foreground"
            title="Le bulletin tel que l'électeur n°1 le remplirait — ce que la règle voit vraiment."
          >
            {Object.entries(result.sample_ballot)
              .sort((a, b) => b[1] - a[1])
              .map(([n, v]) => `${n} ${v}`)
              .join(' · ')}
          </div>
        )}

        {result && (
          <div data-testid="ballot-tradeoff" className="flex flex-col gap-1">
            {(
              [
                [t('method.expressiveness'), result.ballot_expressiveness],
                [t('method.cognitiveLoad'), result.ballot_cognitive_load],
              ] as const
            ).map(([label, v]) => (
              <div key={label} className="flex items-center gap-2 text-[0.7rem]">
                <span className="w-24 shrink-0 text-muted-foreground">{label}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded bg-muted/50">
                  <div
                    className="h-full rounded bg-primary/70"
                    style={{ width: `${v * 100}%`, transition: 'width 300ms ease' }}
                  />
                </div>
                <span className="w-8 text-right font-mono tabular-nums text-muted-foreground">
                  {Math.round(v * 100)}
                </span>
              </div>
            ))}
          </div>
        )}

        {result && result.winner_flips.length > 0 && (
          <p
            data-testid="ballot-flips"
            className="text-[0.7rem] font-medium text-amber-600 dark:text-amber-400"
          >
            {t('method.flips', {
              count: result.winner_flips.length,
              list: result.winner_flips.join(', '),
            })}
          </p>
        )}
        {result && result.incompatible_methods.length > 0 && (
          <p className="text-[0.65rem] text-muted-foreground/70">
            {t('method.incompatible', { count: result.incompatible_methods.length })}
          </p>
        )}
        <Collapsible
          title={t('method.blankAnchorTitle')}
          subtitle={t('method.blankAnchorSub')}
          testid="anchor-blank"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <BlankVoteDivergencePanel />
          </React.Suspense>
        </Collapsible>
      </div>

      {/* Assembly counting rules — the parliament question's "method". */}
      {mode === 'parliament' && (
        <div className="flex flex-col gap-3 rounded-md border border-border p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t('method.assemblyTitle')}
          </p>
          <Field label={t('method.structureLabel')} htmlFor="pg-structure">
            <select
              id="pg-structure"
              className={selectCls}
              value={assembly.structure}
              onChange={(e) => setPlaygroundDeep('assembly.structure', e.target.value)}
            >
              <option value="pr">{t('method.structurePr')}</option>
              <option value="fptp">{t('method.structureFptp')}</option>
              <option value="mmp">{t('method.structureMmp')}</option>
            </select>
          </Field>
          <Field label={t('method.seatsLabel', { n: assembly.seats })} htmlFor="pg-seats">
            <input
              id="pg-seats"
              type="range"
              min={10}
              max={500}
              step={10}
              value={assembly.seats}
              onChange={(e) => setPlaygroundDeep('assembly.seats', Number(e.target.value))}
            />
          </Field>
          <Field
            label={t('method.thresholdLabel', { pct: Math.round(assembly.threshold * 100) })}
            htmlFor="pg-threshold"
          >
            <input
              id="pg-threshold"
              type="range"
              min={0}
              max={0.15}
              step={0.01}
              value={assembly.threshold}
              onChange={(e) => setPlaygroundDeep('assembly.threshold', Number(e.target.value))}
            />
          </Field>
          <Field label={t('method.apportionmentLabel')} htmlFor="pg-appt">
            <select
              id="pg-appt"
              className={selectCls}
              value={assembly.apportionment}
              onChange={(e) => setPlaygroundDeep('assembly.apportionment', e.target.value)}
            >
              <option value="dhondt">{t('method.dhondt')}</option>
              <option value="sainte_lague">{t('method.sainteLague')}</option>
            </select>
          </Field>
        </div>
      )}
    </>
  );
};

export default MethodMoment;
