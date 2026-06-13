import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ElectionConfig } from '../../stores/useElectionStore';
import {
  runStructuralFairness,
  type StructuralFairnessResult,
} from '../../services/structuralApi';
import { PARTY_PALETTE } from './ParliamentCanvas';

// StructuralPanel (frontier FC-2) — the rules AROUND the rule: unequal district
// populations distort vote weight (malapportionment slider), the efficiency gap
// quantifies gerrymanders, the Penrose √-law equalises citizen power in
// councils, and cumulative voting wins minorities the at-large seats that bloc
// voting denies them.

const StructuralPanel: React.FC<{ config: ElectionConfig; partyNames: string[] }> = ({
  config,
  partyNames,
}) => {
  const [mal, setMal] = useState(0.6);
  const [data, setData] = useState<StructuralFairnessResult | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      setData(await runStructuralFairness(config, mal));
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
    <div data-testid="structural-panel" className="flex flex-col gap-2 rounded-md border border-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          ⚖ Équités structurelles
        </span>
        <div className="flex items-center gap-2 text-xs">
          <label
            className="flex items-center gap-1 text-muted-foreground"
            title="0 = circonscriptions de population égale ; 1 = fortement inégales (≈ 4:1)."
          >
            Malapportionnement
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
          <Button data-testid="structural-run" variant="outline" size="sm" onClick={run} disabled={loading}>
            {loading ? '…' : '▶ Analyser'}
          </Button>
        </div>
      </div>
      <p className="text-[0.68rem] text-muted-foreground/70">
        Les règles autour de la règle : taille des circonscriptions, découpage, pondération
        des conseils, scrutin plurinominal — chacune déplace le pouvoir sans toucher au mode
        de scrutin.
      </p>

      {data && (
        <div className="grid grid-cols-1 gap-2 xl:grid-cols-2">
          {/* Malapportionment */}
          <div data-testid="malapportionment-out" className="rounded-md border border-border px-3 py-2 text-xs">
            <p className="font-semibold uppercase tracking-wide text-muted-foreground">
              Poids inégal des voix
            </p>
            <p className="mt-1 tabular-nums">
              Population par siège : rapport{' '}
              <strong>{data.malapportionment.pop_per_seat_ratio.toFixed(1)} : 1</strong>
            </p>
            <p className="tabular-nums">
              Part des voix pouvant contrôler la majorité des sièges :{' '}
              <strong className="text-amber-600 dark:text-amber-400">
                {Math.round(data.malapportionment.min_share_majority_skewed * 100)} %
              </strong>{' '}
              <span className="text-muted-foreground">
                (vs {Math.round(data.malapportionment.min_share_majority_equal * 100)} % à
                circonscriptions égales)
              </span>
            </p>
          </div>

          {/* Efficiency gap */}
          <div data-testid="efficiency-gap-out" className="rounded-md border border-border px-3 py-2 text-xs">
            <p
              className="font-semibold uppercase tracking-wide text-muted-foreground"
              title="(voix gaspillées A − voix gaspillées B) / total bipartite — la métrique standard du charcutage. Gaspillé = voix perdantes + surplus au-delà de 50 % + 1."
            >
              Efficiency gap ({data.efficiency_gap.party_a} vs {data.efficiency_gap.party_b})
            </p>
            <div className="relative mt-1.5 h-3 overflow-hidden rounded bg-muted/50">
              <div className="absolute inset-y-0 left-1/2 w-px bg-foreground/40" />
              <div
                className="absolute inset-y-0 bg-primary/70"
                style={{
                  left: data.efficiency_gap.gap < 0 ? `${50 + data.efficiency_gap.gap * 50}%` : '50%',
                  width: `${Math.abs(data.efficiency_gap.gap) * 50}%`,
                  transition: 'all 300ms ease',
                }}
              />
            </div>
            <p className="mt-1 tabular-nums text-muted-foreground">
              {(data.efficiency_gap.gap * 100).toFixed(1)} % — défavorise{' '}
              <strong>
                {data.efficiency_gap.gap > 0
                  ? data.efficiency_gap.party_a
                  : data.efficiency_gap.party_b}
              </strong>
            </p>
          </div>

          {/* Penrose council */}
          <div data-testid="penrose-out" className="rounded-md border border-border px-3 py-2 text-xs">
            <p
              className="font-semibold uppercase tracking-wide text-muted-foreground"
              title="Pondérer les délégués par √population égalise l'influence des citoyens (approximation de Penrose) ; les pondérations égale ou proportionnelle la déséquilibrent."
            >
              Conseil — loi de Penrose (√)
            </p>
            <div className="mt-1 flex flex-col gap-0.5 tabular-nums">
              {(['equal', 'proportional', 'penrose'] as const).map((scheme) => (
                <div key={scheme} className="flex justify-between">
                  <span className="text-muted-foreground">
                    {scheme === 'equal' ? '1 circonscription = 1 voix'
                      : scheme === 'proportional' ? 'Poids ∝ population'
                      : 'Poids ∝ √population'}
                  </span>
                  <span className={cn(scheme === 'penrose' && 'font-semibold text-green-700 dark:text-green-400')}>
                    pouvoir citoyen max/min : {data.penrose[scheme]?.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Cumulative vs bloc */}
          <div data-testid="cumulative-out" className="rounded-md border border-border px-3 py-2 text-xs">
            <p
              className="font-semibold uppercase tracking-wide text-muted-foreground"
              title="M sièges dans une circonscription unique : en vote en bloc, le parti en tête rafle tout ; en vote cumulatif, une minorité cohésive concentre ses voix et obtient des sièges."
            >
              Plurinominal : bloc vs cumulatif ({data.cumulative.at_large_seats} sièges)
            </p>
            {(['seats_bloc', 'seats_cumulative'] as const).map((key) => (
              <div key={key} className="mt-1 flex items-center gap-2">
                <span className="w-16 shrink-0 text-muted-foreground">
                  {key === 'seats_bloc' ? 'Bloc' : 'Cumulatif'}
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
              Sièges des minorités : {data.cumulative.minority_seats_bloc} (bloc) →{' '}
              <strong
                className={cn(
                  data.cumulative.minority_seats_cumulative >
                    data.cumulative.minority_seats_bloc && 'text-green-700 dark:text-green-400'
                )}
              >
                {data.cumulative.minority_seats_cumulative}
              </strong>{' '}
              (cumulatif)
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default StructuralPanel;
