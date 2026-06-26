import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ElectionConfig, PlaygroundState } from '../../stores/useElectionStore';
import { runStructuralFairness, type StructuralFairnessResult } from '../../services/structuralApi';
import { PARTY_PALETTE } from './ParliamentCanvas';

// StructuralPanel (frontier FC-2) — the rules AROUND the rule: unequal district
// populations distort vote weight (malapportionment slider), the efficiency gap
// quantifies gerrymanders, the Penrose √-law equalises citizen power in
// councils, and cumulative voting wins minorities the at-large seats that bloc
// voting denies them.

const StructuralPanel: React.FC<{
  config: ElectionConfig;
  partyNames: string[];
  playground?: PlaygroundState;
}> = ({ config, partyNames, playground }) => {
  const { t } = useTranslation('playground');
  const [mal, setMal] = useState(0.6);
  const [data, setData] = useState<StructuralFairnessResult | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      setData(await runStructuralFairness(config, mal, 20, 5, playground));
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const colorOf = (name: string): string => {
    const i = partyNames.indexOf(name);
    return PARTY_PALETTE[(i >= 0 ? i : 0) % PARTY_PALETTE.length];
  };

  return (
    <div
      data-testid="structural-panel"
      className="flex flex-col gap-2 rounded-md border border-border p-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('structural.title')}
        </span>
        <div className="flex items-center gap-2 text-xs">
          <label
            className="flex items-center gap-1 text-muted-foreground"
            title={t('structural.malTitle')}
          >
            {t('structural.mal')}
            <input
              data-testid="malapportionment-slider"
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={mal}
              onChange={(e) => setMal(Number(e.target.value))}
            />
            {Math.round(mal * 100)} %
          </label>
          <Button
            data-testid="structural-run"
            variant="outline"
            size="sm"
            onClick={run}
            disabled={loading}
          >
            {loading ? '…' : t('structural.analyze')}
          </Button>
        </div>
      </div>
      <p className="text-[0.68rem] text-muted-foreground/70">{t('structural.intro')}</p>

      {data && (
        <div className="grid grid-cols-1 gap-2 xl:grid-cols-2">
          {/* Malapportionment */}
          <div
            data-testid="malapportionment-out"
            className="rounded-md border border-border px-3 py-2 text-xs"
          >
            <p className="font-semibold uppercase tracking-wide text-muted-foreground">
              {t('structural.unequalWeight')}
            </p>
            <p className="mt-1 tabular-nums">
              {t('structural.popPerSeat')}{' '}
              <strong>{data.malapportionment.pop_per_seat_ratio.toFixed(1)} : 1</strong>
            </p>
            <p className="tabular-nums">
              {t('structural.controlShare')}{' '}
              <strong className="text-amber-600 dark:text-amber-400">
                {Math.round(data.malapportionment.min_share_majority_skewed * 100)} %
              </strong>{' '}
              <span className="text-muted-foreground">
                {t('structural.vsEqual', {
                  pct: Math.round(data.malapportionment.min_share_majority_equal * 100),
                })}
              </span>
            </p>
          </div>

          {/* Efficiency gap */}
          <div
            data-testid="efficiency-gap-out"
            className="rounded-md border border-border px-3 py-2 text-xs"
          >
            <p
              className="font-semibold uppercase tracking-wide text-muted-foreground"
              title={t('structural.egTitle')}
            >
              {t('structural.egLabel', {
                a: data.efficiency_gap.party_a,
                b: data.efficiency_gap.party_b,
              })}
            </p>
            <div className="relative mt-1.5 h-3 overflow-hidden rounded bg-muted/50">
              <div className="absolute inset-y-0 left-1/2 w-px bg-foreground/40" />
              <div
                className="absolute inset-y-0 bg-primary/70"
                style={{
                  left:
                    data.efficiency_gap.gap < 0 ? `${50 + data.efficiency_gap.gap * 50}%` : '50%',
                  width: `${Math.abs(data.efficiency_gap.gap) * 50}%`,
                  transition: 'all 300ms ease',
                }}
              />
            </div>
            <p className="mt-1 tabular-nums text-muted-foreground">
              {t('structural.disfavors', { pct: (data.efficiency_gap.gap * 100).toFixed(1) })}{' '}
              <strong>
                {data.efficiency_gap.gap > 0
                  ? data.efficiency_gap.party_a
                  : data.efficiency_gap.party_b}
              </strong>
            </p>
          </div>

          {/* Penrose council */}
          <div
            data-testid="penrose-out"
            className="rounded-md border border-border px-3 py-2 text-xs"
          >
            <p
              className="font-semibold uppercase tracking-wide text-muted-foreground"
              title={t('structural.penroseTitle')}
            >
              {t('structural.penroseHead')}
            </p>
            <div className="mt-1 flex flex-col gap-0.5 tabular-nums">
              {(['equal', 'proportional', 'penrose'] as const).map((scheme) => (
                <div key={scheme} className="flex justify-between">
                  <span className="text-muted-foreground">
                    {scheme === 'equal'
                      ? t('structural.schemeEqual')
                      : scheme === 'proportional'
                        ? t('structural.schemeProp')
                        : t('structural.schemePenrose')}
                  </span>
                  <span
                    className={cn(
                      scheme === 'penrose' && 'font-semibold text-green-700 dark:text-green-400'
                    )}
                  >
                    {t('structural.citizenPower')} {data.penrose[scheme]?.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Cumulative vs bloc */}
          <div
            data-testid="cumulative-out"
            className="rounded-md border border-border px-3 py-2 text-xs"
          >
            <p
              className="font-semibold uppercase tracking-wide text-muted-foreground"
              title={t('structural.cumTitle')}
            >
              {t('structural.cumHead', { seats: data.cumulative.at_large_seats })}
            </p>
            {(['seats_bloc', 'seats_cumulative'] as const).map((key) => (
              <div key={key} className="mt-1 flex items-center gap-2">
                <span className="w-16 shrink-0 text-muted-foreground">
                  {key === 'seats_bloc' ? t('structural.bloc') : t('structural.cumulative')}
                </span>
                <div className="flex h-4 flex-1 overflow-hidden rounded">
                  {Object.entries(data.cumulative[key])
                    .filter(([, s]) => s > 0)
                    .map(([name, s]) => (
                      <div
                        key={name}
                        title={`${name} : ${s}`}
                        style={{
                          width: `${(s / data.cumulative.at_large_seats) * 100}%`,
                          background: colorOf(name),
                          transition: 'width 300ms ease',
                        }}
                      />
                    ))}
                </div>
              </div>
            ))}
            <p data-testid="minority-lift" className="mt-1 text-muted-foreground">
              {t('structural.minorityLead')} {data.cumulative.minority_seats_bloc}{' '}
              {t('structural.blocSuffix')}{' '}
              <strong
                className={cn(
                  data.cumulative.minority_seats_cumulative > data.cumulative.minority_seats_bloc &&
                    'text-green-700 dark:text-green-400'
                )}
              >
                {data.cumulative.minority_seats_cumulative}
              </strong>{' '}
              {t('structural.cumSuffix')}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default StructuralPanel;
