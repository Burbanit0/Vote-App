import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useInstrumentCtx } from '../playground/PlaygroundController';
import type { Rule } from '../../lib/playgroundVoting';
import { useVotingLabels } from '../../hooks/useVotingLabels';
import { LEADER_RULES, hasFixedWinner, winnersByRule } from '../../lib/scorecard';
import NoFixedWinner from '../playground/NoFixedWinner';
import {
  METHOD_CRITERIA,
  METHOD_CRITERIA_ENTRIES,
  CRITERION_KEYS,
  cite,
  type CriterionBasis,
  type CriterionKey,
  type Satisfaction,
} from '../../data/methodCriteria';
import ReportContentError from '../shared/ui/ReportContentError';
import { METHOD_FAMILY, FAMILY_ORDER, type MethodFamily } from '../../data/methodFamily';
import { candidateColor, textTone } from '../../lib/palette';

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

// What a cell's verdict rests on (method_criteria.json's `basis`).
const BASIS_KEY: Record<CriterionBasis, string> = {
  'engine-tested': 'lab.matrix.basis.engineTested',
  literature: 'lab.matrix.basis.literature',
  variant: 'lab.matrix.basis.variant',
};

const FAMILY_HEADER_CLS: Record<MethodFamily, string> = {
  majoritarian: 'text-violet-700 bg-violet-50 dark:text-violet-300 dark:bg-violet-950/60',
  ordinal: 'text-sky-700 bg-sky-50 dark:text-sky-300 dark:bg-sky-950/60',
  condorcet: 'text-teal-700 bg-teal-50 dark:text-teal-300 dark:bg-teal-950/60',
  cardinal: 'text-orange-700 bg-orange-50 dark:text-orange-300 dark:bg-orange-950/60',
};

const MethodsMatrix: React.FC = () => {
  const { t } = useTranslation('playground');
  const { ruleLabels } = useVotingLabels();
  const { expressedVoters, leaderCandidates } = useInstrumentCtx();

  // Live winners on the expressed ballots, as in the playground.
  const liveWinners = useMemo(
    () => winnersByRule(expressedVoters, leaderCandidates, LEADER_RULES),
    [expressedVoters, leaderCandidates]
  );

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
                  const winIdx = liveWinners[rule] ?? -1;
                  const winner = winIdx >= 0 ? leaderCandidates[winIdx] : undefined;
                  return (
                    <div key={rule} className="flex items-center gap-1.5">
                      <span className="w-36 shrink-0 text-[0.72rem] text-muted-foreground">
                        {ruleLabels[rule]}
                      </span>
                      {!hasFixedWinner(rule) ? (
                        <NoFixedWinner className="text-[0.7rem] font-normal italic text-muted-foreground" />
                      ) : (
                        winner && (
                          <span
                            className="rounded border px-1.5 py-0.5 font-mono text-[0.7rem] font-semibold"
                            style={{
                              color: textTone(candidateColor(winIdx)),
                              borderColor: candidateColor(winIdx) + '55',
                              background: candidateColor(winIdx) + '12',
                            }}
                          >
                            {winner.name}
                          </span>
                        )
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      <CriteriaGrid />
    </div>
  );
};

/** One cell's text, for its tooltip and accessible name and for its open row alike: the
 * heading (method, criterion, verdict) and what the verdict rests on (basis · source, or
 * "to be confirmed" for a literature cell the expert review has yet to source). */
function describeCell(
  rule: Rule,
  crit: CriterionKey,
  label: string,
  t: (key: string) => string
): { heading: string; basis: string } {
  const { verdict, basis, source } = METHOD_CRITERIA_ENTRIES[rule][crit];
  const criterion = t(`lab.matrix.criteria.${crit}`);
  const verdictText = t(`lab.matrix.${verdict}`);
  const heading = `${label} — ${criterion}: ${verdictText}`;
  const parts = [t(BASIS_KEY[basis])];
  if (source) parts.push(`${t('lab.matrix.source')} ${cite(source)}`);
  else if (basis === 'literature') parts.push(t('lab.matrix.unsourced'));
  return { heading, basis: parts.join(' · ') };
}

/** The picked cell's row: what its verdict rests on, the registry's note, and a report link
 * that names the cell. Sticky on the left, so a phone that scrolled the table right still
 * shows it. */
const CellSource: React.FC<{ rule: Rule; crit: CriterionKey; label: string }> = ({
  rule,
  crit,
  label,
}) => {
  const { t } = useTranslation('playground');
  const { heading, basis } = describeCell(rule, crit, label, t);
  const { note } = METHOD_CRITERIA_ENTRIES[rule][crit];
  return (
    <div
      id="matrix-cell-source"
      data-testid="matrix-cell-source"
      role="region"
      aria-label={heading}
      className="sticky left-0 mx-4 my-2 max-w-[calc(100vw-3rem)] rounded-md border border-border bg-muted/30 px-3 py-2 text-[0.72rem]"
    >
      <p className="font-semibold">{heading}</p>
      <p className="mt-1">{basis}</p>
      {note && (
        <p className="mt-1 text-muted-foreground">
          {t('lab.matrix.note')} <span lang="en">{note}</span>
        </p>
      )}
      <div className="mt-1">
        <ReportContentError where={`matrix:${rule}/${crit}`} />
      </div>
    </div>
  );
};

/** The static criteria grid: it reads no live data, so a candidate drag (which re-renders
 * MethodsMatrix through useInstrumentCtx) leaves it alone. */
const CriteriaGrid: React.FC = React.memo(function CriteriaGrid() {
  const { t } = useTranslation('playground');
  const { ruleLabels } = useVotingLabels();
  // The cell whose basis and source open under its row (W1.4).
  const [picked, setPicked] = useState<{ rule: Rule; crit: CriterionKey } | null>(null);

  return (
    <>
      <div className="overflow-x-auto" data-touch>
        <table className="w-full border-collapse text-[0.72rem]">
          <thead>
            <tr className="border-b border-border">
              <th className="w-36 py-2 pl-4 pr-2 text-left font-mono text-[0.6rem] uppercase tracking-wider text-muted-foreground">
                {t('lab.matrix.colMethod')}
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
                  <React.Fragment key={rule}>
                    <tr
                      className={`border-b border-border/50 ${rowIdx % 2 === 0 ? '' : 'bg-muted/20'}`}
                    >
                      <td className="py-1.5 pl-4 pr-2 text-muted-foreground">{ruleLabels[rule]}</td>
                      {CRITERION_KEYS.map((crit) => {
                        const sat = METHOD_CRITERIA[rule][crit];
                        const { symbol, cls } = CELL[sat];
                        const isPicked = picked?.rule === rule && picked.crit === crit;
                        const { heading, basis } = describeCell(rule, crit, ruleLabels[rule], t);
                        const label = `${heading} · ${basis}`;
                        return (
                          <td key={crit} className="px-1 py-1.5 text-center">
                            <button
                              type="button"
                              data-testid={`matrix-cell-${rule}-${crit}`}
                              aria-expanded={isPicked}
                              aria-controls={isPicked ? 'matrix-cell-source' : undefined}
                              onClick={() => setPicked(isPicked ? null : { rule, crit })}
                              title={label}
                              aria-label={label}
                              className={`inline-block rounded px-1 font-mono font-bold ${cls} ${isPicked ? 'ring-2 ring-primary' : ''}`}
                            >
                              {symbol}
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                    {picked?.rule === rule && (
                      <tr>
                        <td colSpan={CRITERION_KEYS.length + 1}>
                          <CellSource rule={rule} crit={picked.crit} label={ruleLabels[rule]} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        {/* Legend */}
        <div className="flex flex-wrap gap-4 px-4 py-2 text-[0.68rem] text-muted-foreground">
          <span>
            <span className={`font-mono font-bold ${CELL.yes.cls} rounded px-1`}>✓</span>{' '}
            {t('lab.matrix.yes')}
          </span>
          <span>
            <span className={`font-mono font-bold ${CELL.no.cls} rounded px-1`}>✗</span>{' '}
            {t('lab.matrix.no')}
          </span>
          <span>
            <span className={`font-mono font-bold ${CELL.conditional.cls} rounded px-1`}>◐</span>{' '}
            {t('lab.matrix.conditional')}
          </span>
          <span className="italic">{t('lab.matrix.cellHint')}</span>
        </div>
      </div>
    </>
  );
});

export default MethodsMatrix;
