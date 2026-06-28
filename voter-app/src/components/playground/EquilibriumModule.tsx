import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { type NamedPt, type Pt, type Rule } from '../../lib/playgroundVoting';
import { useVotingLabels } from '../../hooks/useVotingLabels';
import { equilibriumReport, type EquilibriumReport } from '../../lib/playgroundEquilibrium';

// EquilibriumModule — the dynamic face of the sincerity question. SincerityModule
// asks "would ONE bloc deviate?"; this plays the deviations out: every camp keeps
// best-responding until the ballots settle (or won't). The payload is the thesis
// under strategic play — which methods elect their sincere winner anyway, which
// get pushed onto someone else, and which never settle. On-demand (it sweeps all
// rules), like the electorate scan it sits beside.

const EquilibriumModule: React.FC<{ voters: Pt[]; candidates: NamedPt[] }> = ({
  voters,
  candidates,
}) => {
  const { t } = useTranslation('playground');
  const { ruleLabels } = useVotingLabels();
  const label = (r: Rule) => ruleLabels[r] ?? r;

  const [report, setReport] = React.useState<EquilibriumReport | null>(null);
  // Drop a stale result when the electorate or candidates change underneath it.
  React.useEffect(() => setReport(null), [voters, candidates]);

  const shifted = report?.verdicts.filter((v) => v.outcome === 'shifted') ?? [];
  const cycles = report?.verdicts.filter((v) => v.outcome === 'cycle') ?? [];
  const stable = report?.verdicts.filter((v) => v.outcome === 'stable') ?? [];

  return (
    <div data-testid="equilibrium-module" className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground/80">{t('equilibrium.intro')}</p>
      <Button
        data-testid="equilibrium-run"
        variant="outline"
        size="sm"
        className="self-start"
        onClick={() => setReport(equilibriumReport(voters, candidates))}
        title={t('equilibrium.runTitle')}
      >
        {report ? t('equilibrium.rerun') : t('equilibrium.run')}
      </Button>

      {report && report.groups > 0 && (
        <div className="flex flex-col gap-2">
          <p data-testid="equilibrium-headline" className="text-sm">
            {t('equilibrium.headlinePre')}{' '}
            <strong className="text-amber-600 dark:text-amber-400">{shifted.length}</strong>{' '}
            {t('equilibrium.headlineEnd', { groups: report.groups })}
          </p>

          {shifted.length > 0 && (
            <div data-testid="equilibrium-shifted" className="flex flex-col gap-1">
              <p className="text-[0.65rem] font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">
                {t('equilibrium.shiftedHead')}
              </p>
              {shifted.map((v) => (
                <div
                  key={v.rule}
                  className="flex flex-col rounded bg-amber-500/10 px-2 py-1 text-xs"
                >
                  <span className="font-medium">{label(v.rule)}</span>
                  <span className="text-[0.7rem] text-muted-foreground">
                    <strong>{v.sincereWinner}</strong> →{' '}
                    <strong className="text-amber-700 dark:text-amber-300">
                      {v.equilibriumWinner}
                    </strong>{' '}
                    <em>{t('equilibrium.afterPasses', { n: v.passes })}</em>
                  </span>
                </div>
              ))}
            </div>
          )}

          {cycles.length > 0 && (
            <div data-testid="equilibrium-cycles" className="flex flex-col gap-1">
              <p className="text-[0.65rem] font-semibold uppercase tracking-wide text-red-600 dark:text-red-400">
                {t('equilibrium.cycleHead')}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {cycles.map((v) => (
                  <span
                    key={v.rule}
                    className="rounded border border-red-500/40 px-1.5 py-0.5 text-[0.7rem] text-muted-foreground"
                    title={t('equilibrium.cycleTitle')}
                  >
                    {label(v.rule)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {stable.length > 0 && (
            <div data-testid="equilibrium-stable" className="flex flex-col gap-1">
              <p className="text-[0.65rem] font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
                {t('equilibrium.stableHead')}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {stable.map((v) => (
                  <span
                    key={v.rule}
                    className="rounded border border-border px-1.5 py-0.5 text-[0.7rem] text-muted-foreground"
                    title={t('equilibrium.elects', { winner: v.sincereWinner })}
                  >
                    {label(v.rule)}
                  </span>
                ))}
              </div>
            </div>
          )}

          <p className="text-[0.65rem] text-muted-foreground">{t('equilibrium.note')}</p>
        </div>
      )}
    </div>
  );
};

export default EquilibriumModule;
