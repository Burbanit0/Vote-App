import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { usePlaygroundCtx } from '../PlaygroundController';
import Scorecard from '../Scorecard';
import MethodInfo from '../MethodInfo';
import MethodReplayModal from '../MethodReplayModal';
import Collapsible from '../Collapsible';
import { useVotingLabels } from '../../../hooks/useVotingLabels';
import { ruleWinner, type Rule } from '../../../lib/playgroundVoting';
import { LEADER_RULES } from '../../../lib/scorecard';
import { METHOD_FAMILY, FAMILY_ORDER, type MethodFamily } from '../../../data/methodCriteria';
import { CANDIDATE_COLORS_LIGHT } from '../../../constants/chartColors';

const rulesByFamily = (rules: Rule[]): Record<MethodFamily, Rule[]> =>
  FAMILY_ORDER.reduce(
    (acc, fam) => ({ ...acc, [fam]: rules.filter((r) => METHOD_FAMILY[r] === fam) }),
    {} as Record<MethodFamily, Rule[]>
  );

const FAMILY_LABEL_KEY: Record<MethodFamily, string> = {
  majoritarian: 'lab.matrix.familyMajoritarian',
  ordinal: 'lab.matrix.familyOrdinal',
  condorcet: 'lab.matrix.familyCondorcet',
  cardinal: 'lab.matrix.familyCardinal',
};

const FAMILY_HEADER_CLS: Record<MethodFamily, string> = {
  majoritarian: 'text-violet-700 bg-violet-50 dark:text-violet-300 dark:bg-violet-950/60',
  ordinal: 'text-sky-700 bg-sky-50 dark:text-sky-300 dark:bg-sky-950/60',
  condorcet: 'text-teal-700 bg-teal-50 dark:text-teal-300 dark:bg-teal-950/60',
  cardinal: 'text-orange-700 bg-orange-50 dark:text-orange-300 dark:bg-orange-950/60',
};

function MiniBar({ mean, lo, hi }: { mean: number; lo: number; hi: number }) {
  return (
    <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted/60">
      <div
        className="absolute inset-y-0 rounded-full bg-primary/30"
        style={{ left: `${lo * 100}%`, width: `${Math.max(2, (hi - lo) * 100)}%` }}
      />
      <div
        className="absolute inset-y-0 w-0.5 rounded bg-primary"
        style={{ left: `calc(${mean * 100}% - 1px)` }}
      />
    </div>
  );
}

// One resistance axis for a method: the range band + mean tick, now with the mean
// score spelled out (0–100) so the column reads at a glance, not just as a bar.
function AxisCell({ axis }: { axis?: { mean: number; lo: number; hi: number } }) {
  if (!axis) return <div className="h-1.5 animate-pulse rounded bg-muted/40" />;
  return (
    <div className="flex items-center gap-1.5">
      <MiniBar {...axis} />
      <span className="w-7 shrink-0 text-right text-[0.68rem] font-medium tabular-nums">
        {Math.round(axis.mean * 100)}
      </span>
    </div>
  );
}

// Moment ⑤ Bilan — cross-method comparison: who wins, and how robust is each
// verdict? Three resistance axes (stability, strategic, Condorcet) come from the
// Monte-Carlo scorecard already computed for the values lens — no extra cost.
const BilanMoment: React.FC = () => {
  const { t } = useTranslation('playground');
  const { ruleLabels, structureLabels } = useVotingLabels();
  const {
    mode,
    assembly,
    parlSc,
    currentAxes,
    leaderSc,
    result,
    votingVoters,
    leaderCandidates,
    enabledRules,
  } = usePlaygroundCtx();
  const [replayRule, setReplayRule] = useState<Rule | null>(null);

  // Moment ② is explicit about it ("seules les méthodes cochées apparaissent dans
  // le bilan"): the whole synthesis below is scoped to the compared set.
  const activeRules = useMemo(
    () => LEADER_RULES.filter((r) => enabledRules.has(r)),
    [enabledRules]
  );
  const familyRules = useMemo(() => rulesByFamily(activeRules), [activeRules]);

  const liveWinners = useMemo(() => {
    if (!votingVoters.length || !leaderCandidates.length) return {} as Record<Rule, number>;
    return activeRules.reduce(
      (acc, rule) => {
        acc[rule] = ruleWinner(votingVoters, leaderCandidates, rule);
        return acc;
      },
      {} as Record<Rule, number>
    );
  }, [votingVoters, leaderCandidates, activeRules]);

  // Group methods by the candidate they elect (most-backed first) — the synthesis
  // that makes the thesis literal: does the winner depend on the rule?
  const winnerGroups = useMemo(() => {
    const m = new Map<number, Rule[]>();
    for (const rule of activeRules) {
      const idx = liveWinners[rule];
      if (idx == null || idx < 0) continue;
      const arr = m.get(idx) ?? [];
      arr.push(rule);
      m.set(idx, arr);
    }
    return [...m.entries()].sort((a, b) => b[1].length - a[1].length);
  }, [liveWinners, activeRules]);

  const condorcetName = result?.condorcet_winner ?? null;
  const condorcetIdx = condorcetName
    ? leaderCandidates.findIndex((c) => c.name === condorcetName)
    : -1;

  const candColor = (idx: number) => CANDIDATE_COLORS_LIGHT[idx % CANDIDATE_COLORS_LIGHT.length];

  return (
    <div className="flex flex-col gap-4">
      {replayRule && (
        <MethodReplayModal
          show
          onHide={() => setReplayRule(null)}
          voters={votingVoters}
          candidates={leaderCandidates}
          initialRule={replayRule}
        />
      )}
      {mode === 'leader' ? (
        <>
          {/* ── 1. The verdict: does the winner depend on the method? ── */}
          <div
            data-testid="bilan-verdict"
            className="rounded-lg border border-border bg-muted/20 p-4"
          >
            <p className="font-mono text-[0.6rem] uppercase tracking-[0.2em] text-primary">
              {t('bilan.verdictTitle')}
            </p>
            {winnerGroups.length > 1 ? (
              <>
                <p className="mt-1 font-display text-2xl font-bold tracking-tight">
                  {t('bilan.verdictSplit', { count: winnerGroups.length })}
                </p>
                <p className="mt-0.5 text-sm text-muted-foreground">{t('bilan.verdictSplitSub')}</p>
              </>
            ) : (
              <>
                <p
                  className="mt-1 font-display text-2xl font-bold tracking-tight"
                  style={{ color: candColor(winnerGroups[0]?.[0] ?? 0) }}
                >
                  {t('bilan.verdictConsensus', {
                    name: leaderCandidates[winnerGroups[0]?.[0] ?? 0]?.name ?? '—',
                  })}
                </p>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  {t('bilan.verdictConsensusSub')}
                </p>
              </>
            )}
            <p className="mt-2 text-xs text-muted-foreground">
              {condorcetName
                ? t('bilan.condorcetIs', { name: condorcetName })
                : t('bilan.condorcetNone')}
            </p>
          </div>

          {/* ── 2. Who wins, and with which methods (grouped by laureate) ── */}
          <div className="flex flex-col gap-2">
            <p className="text-sm font-semibold">{t('bilan.winnersTitle')}</p>
            {winnerGroups.map(([idx, rules]) => (
              <div
                key={idx}
                data-testid={`winner-group-${idx}`}
                className="flex items-start gap-3 rounded-md border border-border p-3"
              >
                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className="inline-block h-3.5 w-3.5 rounded-full"
                    style={{ background: candColor(idx) }}
                  />
                  <span
                    className="font-display text-lg font-bold"
                    style={{ color: candColor(idx) }}
                  >
                    {leaderCandidates[idx]?.name ?? '—'}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-muted-foreground">
                      {rules.length === 1
                        ? t('bilan.methodCountOne')
                        : t('bilan.methodCountMany', { count: rules.length })}
                    </span>
                    {idx === condorcetIdx && (
                      <span className="rounded-full bg-teal-100 px-2 py-0.5 text-[0.62rem] font-semibold uppercase tracking-wide text-teal-700 dark:bg-teal-950/60 dark:text-teal-300">
                        {t('bilan.condorcetBadge')}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {rules.map((r) => ruleLabels[r]).join(' · ')}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* ── 3. Robustness detail (per-method resistance + replay) ── */}
          <Collapsible
            title={t('bilan.robustnessTitle')}
            subtitle={t('bilan.robustnessSub', { count: 20 })}
            testid="module-robustness"
          >
            <div className="flex flex-col gap-1.5">
              <div
                data-testid="bilan-method-table"
                className="overflow-x-auto rounded-md border border-border"
              >
                <table className="w-full border-collapse text-[0.72rem]">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="py-1.5 pl-3 pr-2 text-left font-mono text-[0.6rem] uppercase tracking-wider text-muted-foreground">
                        {t('bilan.colMethod')}
                      </th>
                      <th className="px-2 py-1.5 text-left font-mono text-[0.6rem] uppercase tracking-wider text-muted-foreground">
                        {t('bilan.colWinner')}
                      </th>
                      <th
                        className="w-28 px-2 py-1.5 text-left font-mono text-[0.6rem] uppercase tracking-wider text-muted-foreground"
                        title={t('axes.stability.hint')}
                      >
                        {t('bilan.colStability')}
                      </th>
                      <th
                        className="w-28 px-2 py-1.5 text-left font-mono text-[0.6rem] uppercase tracking-wider text-muted-foreground"
                        title={t('axes.strategic_resistance.hint')}
                      >
                        {t('bilan.colStrategy')}
                      </th>
                      <th
                        className="w-28 px-2 py-1.5 text-left font-mono text-[0.6rem] uppercase tracking-wider text-muted-foreground"
                        title={t('axes.condorcet_efficiency.hint')}
                      >
                        {t('bilan.colCondorcet')}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {FAMILY_ORDER.filter((fam) => familyRules[fam].length > 0).map((fam) => (
                      <React.Fragment key={fam}>
                        <tr className={FAMILY_HEADER_CLS[fam]}>
                          <td
                            colSpan={5}
                            className="py-0.5 pl-3 font-mono text-[0.58rem] font-semibold uppercase tracking-wider"
                          >
                            {t(FAMILY_LABEL_KEY[fam])}
                          </td>
                        </tr>
                        {familyRules[fam].map((rule, i) => {
                          const winIdx = liveWinners[rule] ?? 0;
                          const winner = leaderCandidates[winIdx];
                          const axes = leaderSc?.[rule];
                          return (
                            <tr
                              key={rule}
                              className={`border-b border-border/40 ${i % 2 === 0 ? '' : 'bg-muted/15'}`}
                            >
                              <td className="py-1.5 pl-3 pr-2">
                                <button
                                  type="button"
                                  data-testid={`replay-row-${rule}`}
                                  onClick={() => setReplayRule(rule)}
                                  className="text-left text-muted-foreground hover:text-primary hover:underline"
                                  title={t('canvas.replayCta')}
                                >
                                  {ruleLabels[rule]}
                                </button>
                              </td>
                              <td className="px-2 py-1.5">
                                {winner && (
                                  <span
                                    className="rounded border px-1.5 py-0.5 font-mono text-[0.68rem] font-semibold"
                                    style={{
                                      color: candColor(winIdx),
                                      borderColor: `${candColor(winIdx)}55`,
                                      background: `${candColor(winIdx)}12`,
                                    }}
                                  >
                                    {winner.name}
                                  </span>
                                )}
                              </td>
                              <td className="px-2 py-1.5">
                                <AxisCell axis={axes?.stability} />
                              </td>
                              <td className="px-2 py-1.5">
                                <AxisCell axis={axes?.strategic_resistance} />
                              </td>
                              <td className="px-2 py-1.5">
                                <AxisCell axis={axes?.condorcet_efficiency} />
                              </td>
                            </tr>
                          );
                        })}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
              {leaderSc && (
                <div className="flex flex-col gap-1 rounded-md bg-muted/20 px-2.5 py-2 text-[0.68rem] text-muted-foreground">
                  <p className="font-medium text-foreground/80">
                    {t('bilan.robustnessLegend', { count: 20 })}
                  </p>
                  {(
                    [
                      ['stability', 'colStability'],
                      ['strategic_resistance', 'colStrategy'],
                      ['condorcet_efficiency', 'colCondorcet'],
                    ] as const
                  ).map(([axis, col]) => (
                    <p key={axis}>
                      <strong className="text-foreground/70">{t(`bilan.${col}`)}</strong> —{' '}
                      {t(`axes.${axis}.hint`)}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </Collapsible>
        </>
      ) : (
        <>
          {/* Parliament mode — single-structure scorecard */}
          <div className="flex items-center gap-1 text-sm font-medium">
            <span className="text-muted-foreground">{t('bilan.evaluatedFor')}</span>
            <span>{structureLabels[assembly.structure]}</span>
            <MethodInfo method={assembly.structure} placement="bottom" />
          </div>
          <Scorecard
            axes={currentAxes}
            bandNote={t('bilan.bandNote', { count: parlSc?.replications ?? 24 })}
          />
        </>
      )}

      <hr className="border-border" />

      <div className="text-center">
        <p className="text-xs text-muted-foreground">{t('bilan.labCtaNote')}</p>
        <Link
          to="/laboratoire"
          data-testid="bilan-lab-link"
          className="mt-1 inline-block text-sm text-primary hover:underline"
        >
          {t('bilan.labCta')}
        </Link>
      </div>
    </div>
  );
};

export default BilanMoment;
