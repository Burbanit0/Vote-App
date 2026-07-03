import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { usePlaygroundCtx } from '../playground/PlaygroundController';
import { ruleWinner, RULE_LABELS, type Rule } from '../../lib/playgroundVoting';
import { LEADER_RULES } from '../../lib/scorecard';
import {
  METHOD_CRITERIA,
  METHOD_FAMILY,
  FAMILY_ORDER,
  CRITERION_KEYS,
  type CriterionKey,
  type Satisfaction,
  type MethodFamily,
} from '../../data/methodCriteria';
import { CANDIDATE_COLORS_LIGHT } from '../../constants/chartColors';

// Only the compared methods (Tier A) — Tier B extras live in the method gallery.
const RULES_BY_FAMILY: Record<MethodFamily, Rule[]> = FAMILY_ORDER.reduce(
  (acc, fam) => ({
    ...acc,
    [fam]: LEADER_RULES.filter((r) => METHOD_FAMILY[r] === fam),
  }),
  {} as Record<MethodFamily, Rule[]>
);

const FAMILY_LABEL_KEY: Record<MethodFamily, string> = {
  majoritarian: 'lab.matrix.familyMajoritarian',
  ordinal: 'lab.matrix.familyOrdinal',
  condorcet: 'lab.matrix.familyCondorcet',
  cardinal: 'lab.matrix.familyCardinal',
};

const CELL: Record<Satisfaction, { symbol: string; cls: string }> = {
  yes: { symbol: '✓', cls: 'text-green-700 bg-green-50 dark:text-green-400 dark:bg-green-950' },
  no: { symbol: '✗', cls: 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950' },
  conditional: {
    symbol: '◐',
    cls: 'text-amber-700 bg-amber-50 dark:text-amber-400 dark:bg-amber-950',
  },
};

const FAMILY_HEADER_CLS: Record<MethodFamily, string> = {
  majoritarian: 'text-violet-700 bg-violet-50 dark:text-violet-300 dark:bg-violet-950/60',
  ordinal: 'text-sky-700 bg-sky-50 dark:text-sky-300 dark:bg-sky-950/60',
  condorcet: 'text-teal-700 bg-teal-50 dark:text-teal-300 dark:bg-teal-950/60',
  cardinal: 'text-orange-700 bg-orange-50 dark:text-orange-300 dark:bg-orange-950/60',
};

const MethodsMatrix: React.FC = () => {
  const { t } = useTranslation('playground');
  const { voters, leaderCandidates } = usePlaygroundCtx();

  // Live winners — one ruleWinner() call per rule on the current electorate
  const liveWinners = useMemo<Record<Rule, number>>(() => {
    if (!voters.length || !leaderCandidates.length) return {} as Record<Rule, number>;
    return LEADER_RULES.reduce(
      (acc, rule) => {
        acc[rule] = ruleWinner(voters, leaderCandidates, rule);
        return acc;
      },
      {} as Record<Rule, number>
    );
  }, [voters, leaderCandidates]);

  const candidateColor = (idx: number) =>
    CANDIDATE_COLORS_LIGHT[idx % CANDIDATE_COLORS_LIGHT.length];

  return (
    <div className="rounded-xl border border-border bg-card">
      {/* ── Header ── */}
      <div className="border-b border-border px-4 py-3">
        <p className="font-mono text-[0.68rem] uppercase tracking-[0.2em] text-primary">
          {t('lab.eyebrow')}
        </p>
        <h2 className="mt-0.5 font-display text-base font-bold tracking-tight">
          {t('lab.matrix.title')}
        </h2>
      </div>

      {/* ── Live winners row ── */}
      <div className="border-b border-border px-4 py-3">
        <p className="mb-2 font-mono text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">
          {t('lab.matrix.liveRow')}
        </p>
        <div className="flex flex-wrap gap-x-6 gap-y-3">
          {FAMILY_ORDER.map((fam) => (
            <div key={fam} className="flex flex-col gap-1.5">
              <span
                className={`inline-block rounded px-1.5 py-0.5 font-mono text-[0.6rem] font-semibold uppercase tracking-wider ${FAMILY_HEADER_CLS[fam]}`}
              >
                {t(FAMILY_LABEL_KEY[fam])}
              </span>
              <div className="flex flex-col gap-1">
                {RULES_BY_FAMILY[fam].map((rule) => {
                  const winIdx = liveWinners[rule] ?? 0;
                  const winner = leaderCandidates[winIdx];
                  return (
                    <div key={rule} className="flex items-center gap-1.5">
                      <span className="w-36 shrink-0 text-[0.72rem] text-muted-foreground">
                        {RULE_LABELS[rule]}
                      </span>
                      {winner && (
                        <span
                          className="rounded border px-1.5 py-0.5 font-mono text-[0.7rem] font-semibold"
                          style={{
                            color: candidateColor(winIdx),
                            borderColor: candidateColor(winIdx) + '55',
                            background: candidateColor(winIdx) + '12',
                          }}
                        >
                          {winner.name}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Static criteria grid ── */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[0.72rem]">
          <thead>
            <tr className="border-b border-border">
              <th className="w-36 py-2 pl-4 pr-2 text-left font-mono text-[0.6rem] uppercase tracking-wider text-muted-foreground">
                Méthode
              </th>
              {CRITERION_KEYS.map((crit) => (
                <th
                  key={crit}
                  className="px-1 py-2 text-center font-mono text-[0.6rem] uppercase tracking-wider text-muted-foreground"
                  title={t(`lab.matrix.criteria.${crit as CriterionKey}`)}
                >
                  <span className="hidden sm:inline">
                    {t(`lab.matrix.criteria.${crit as CriterionKey}`)}
                  </span>
                  <span className="sm:hidden" aria-hidden>
                    {crit.slice(0, 3)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FAMILY_ORDER.map((fam) => (
              <React.Fragment key={fam}>
                <tr className={FAMILY_HEADER_CLS[fam]}>
                  <td
                    colSpan={CRITERION_KEYS.length + 1}
                    className="py-1 pl-4 font-mono text-[0.6rem] font-semibold uppercase tracking-wider"
                  >
                    {t(FAMILY_LABEL_KEY[fam])}
                  </td>
                </tr>
                {RULES_BY_FAMILY[fam].map((rule, rowIdx) => (
                  <tr
                    key={rule}
                    className={`border-b border-border/50 ${rowIdx % 2 === 0 ? '' : 'bg-muted/20'}`}
                  >
                    <td className="py-1.5 pl-4 pr-2 text-muted-foreground">{RULE_LABELS[rule]}</td>
                    {CRITERION_KEYS.map((crit) => {
                      const sat = METHOD_CRITERIA[rule][crit];
                      const { symbol, cls } = CELL[sat];
                      return (
                        <td
                          key={crit}
                          className="px-1 py-1.5 text-center"
                          title={`${RULE_LABELS[rule]} — ${t(`lab.matrix.criteria.${crit as CriterionKey}`)}: ${sat}`}
                        >
                          <span className={`inline-block rounded px-1 font-mono font-bold ${cls}`}>
                            {symbol}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        {/* Legend */}
        <div className="flex gap-4 px-4 py-2 text-[0.68rem] text-muted-foreground">
          <span>
            <span className={`font-mono font-bold ${CELL.yes.cls} rounded px-1`}>✓</span> Oui
          </span>
          <span>
            <span className={`font-mono font-bold ${CELL.no.cls} rounded px-1`}>✗</span> Non
          </span>
          <span>
            <span className={`font-mono font-bold ${CELL.conditional.cls} rounded px-1`}>◐</span>{' '}
            Conditionnel
          </span>
        </div>
      </div>
    </div>
  );
};

export default MethodsMatrix;
