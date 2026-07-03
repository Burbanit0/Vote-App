import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import type { ElectionConfig, PlaygroundState } from '../../stores/useElectionStore';
import { runProfileSimulate } from '../../services/profileApi';
import { type Rule } from '../../lib/playgroundVoting';
import { useVotingLabels } from '../../hooks/useVotingLabels';

// StrategicModule (on-demand) — three per-method strategy signals:
//  · manipulability rate (Gibbard–Satterthwaite, brute-force ballot perturbation);
//  · no-show / participation — computed LIVE on this electorate (a favourite-group
//    that would gain by abstaining);
//  · Later-No-Harm — a KNOWN, profile-invariant property (literature), so it is a
//    static table, not a shaky live search.
// The backend passes O(voters × methods × perms), ~seconds → on demand only.

// Later-No-Harm is satisfied by exactly the "first-preference-only until eliminated"
// family; every scoring/Condorcet/median rule can be harmed by a lower ranking.
const LNH_SATISFIES = new Set<string>(['plurality', 'two_round', 'irv', 'random_ballot']);

interface StratRow {
  name: string;
  sv: number;
  noShow: boolean;
}

const StrategicModule: React.FC<{ config: ElectionConfig; playground: PlaygroundState }> = ({
  config,
  playground,
}) => {
  const { t } = useTranslation('playground');
  const { ruleLabels } = useVotingLabels();
  const [rows, setRows] = useState<StratRow[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const run = async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await runProfileSimulate(config, playground, true);
      const out: StratRow[] = Object.entries(res.methods)
        .map(([name, m]) => ({
          name,
          sv: m.strategic_vulnerability ?? -1,
          noShow: m.no_show ?? false,
        }))
        .filter((r) => r.sv >= 0)
        .sort((a, b) => a.sv - b.sv); // most resistant first
      setRows(out);
    } catch {
      setError(true);
      setRows(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="strategic-module" className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground/80">{t('strategy.svIntro')}</p>
      <Button
        data-testid="strategic-run"
        variant="outline"
        size="sm"
        className="self-start"
        onClick={run}
        disabled={loading}
      >
        {loading ? t('strategy.svComputing') : t('strategy.svRun')}
      </Button>

      {error && (
        <p className="text-xs text-amber-600 dark:text-amber-400">{t('strategy.svError')}</p>
      )}

      {rows && (
        <div data-testid="strategic-rows" className="flex flex-col gap-1">
          {/* Column header: manipulability bar, then the two axiom flags. Cells are
              divs (not spans) so the row-label spans below stay first in the DOM. */}
          <div className="flex items-center gap-2 text-[0.6rem] uppercase tracking-wide text-muted-foreground/70">
            <div className="w-40 shrink-0" />
            <div className="flex-1">{t('strategy.svColManip')}</div>
            <div className="w-10" />
            <div className="w-12 shrink-0 text-center">{t('strategy.svColNoShow')}</div>
            <div className="w-8 shrink-0 text-center">{t('strategy.svColLnh')}</div>
          </div>
          {rows.map(({ name, sv, noShow }) => {
            const lnh = LNH_SATISFIES.has(name);
            return (
              <div key={name} className="flex items-center gap-2 text-xs">
                <span className="w-40 shrink-0 truncate text-muted-foreground">
                  {ruleLabels[name as Rule] ?? name}
                </span>
                <div className="h-2.5 flex-1 overflow-hidden rounded bg-muted/50">
                  <div
                    className="h-full rounded bg-amber-500/70"
                    style={{ width: `${sv * 100}%`, transition: 'width 300ms ease' }}
                  />
                </div>
                <span className="w-10 text-right tabular-nums text-muted-foreground">
                  {Math.round(sv * 100)} %
                </span>
                <span
                  className="w-12 shrink-0 text-center"
                  title={t(noShow ? 'strategy.svNoShowYes' : 'strategy.svNoShowNo')}
                >
                  {noShow ? (
                    <span className="text-amber-600 dark:text-amber-400">⚠</span>
                  ) : (
                    <span className="text-muted-foreground/40">·</span>
                  )}
                </span>
                <span
                  className="w-8 shrink-0 text-center"
                  title={t(lnh ? 'strategy.svLnhOk' : 'strategy.svLnhFail')}
                >
                  {lnh ? (
                    <span className="text-green-600 dark:text-green-400">✓</span>
                  ) : (
                    <span className="text-red-500/70">✗</span>
                  )}
                </span>
              </div>
            );
          })}
          <p className="text-[0.65rem] text-muted-foreground">{t('strategy.svFooter')}</p>
          <p className="text-[0.65rem] text-muted-foreground/80">{t('strategy.svAxiomFooter')}</p>
        </div>
      )}
    </div>
  );
};

export default StrategicModule;
