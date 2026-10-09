import React from 'react';
import { useTranslation } from 'react-i18next';
import { useVotingLabels } from '../../hooks/useVotingLabels';
import {
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  type Rule,
} from '../../lib/playgroundVoting';
import { LEADER_RULES } from '../../lib/scorecard';
import { candidateColor, textTone } from '../../lib/palette';
import {
  useStoreCtx,
  useJourneyCtx,
  useInstrumentCtx,
  useMethodSelection,
} from './PlaygroundController';

/** Winner strip, above every moment: who the rule on the map elects, and what the
 * other ticked methods elect, on the same expressed ballots as the map. Leader mode
 * only; the assembly's result is its seat chart. A random ballot has no fixed winner
 * (the engine's deterministic stand-in is plurality's), so it never "elects" anyone. */
const WinnerStrip: React.FC = () => {
  const { t } = useTranslation('playground');
  const { ruleLabels } = useVotingLabels();
  const { mode, behavior } = useStoreCtx();
  const { leaderRule } = useJourneyCtx();
  const { expressedVoters, leaderCandidates } = useInstrumentCtx();
  const { enabledRules } = useMethodSelection();

  const others = React.useMemo(() => {
    const m = leaderCandidates.length;
    if (mode !== 'leader' || m === 0 || expressedVoters.length === 0) return null;
    const ranks = computeRanks(expressedVoters, leaderCandidates);
    const scores = computeScores(expressedVoters, leaderCandidates);
    const winnerOf = (r: Rule) => ruleWinnerFromRanks(ranks, m, r, scores);
    const groups = new Map<number, Rule[]>();
    for (const r of LEADER_RULES) {
      if (r === leaderRule || r === 'random_ballot' || !enabledRules.has(r)) continue;
      const w = winnerOf(r);
      if (w >= 0) groups.set(w, [...(groups.get(w) ?? []), r]);
    }
    return { current: leaderRule === 'random_ballot' ? -1 : winnerOf(leaderRule), groups };
  }, [mode, expressedVoters, leaderCandidates, leaderRule, enabledRules]);

  if (!others) return null;
  const { current, groups } = others;
  const othersCount = [...groups.values()].reduce((n, rs) => n + rs.length, 0);
  const name = (i: number) => (
    <strong style={{ color: textTone(candidateColor(i)) }}>{leaderCandidates[i]?.name}</strong>
  );

  return (
    <div
      data-testid="winner-strip"
      className="mt-3 flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-lg border border-border bg-muted/20 px-4 py-2 text-sm"
    >
      <span data-testid="winner-strip-current" className="font-display text-base">
        {t('strip.under', { rule: ruleLabels[leaderRule] })}{' '}
        {current >= 0 ? (
          name(current)
        ) : (
          <strong data-testid="no-fixed-winner" title={t('strip.noFixedWinnerTitle')}>
            {t('strip.noFixedWinner')}
          </strong>
        )}
      </span>
      {othersCount > 0 && (
        <span data-testid="winner-strip-others" className="text-muted-foreground">
          {groups.size === 1 && groups.has(current) ? (
            t('strip.othersAgree', { count: othersCount })
          ) : (
            <>
              {t('strip.othersElect')}{' '}
              {[...groups.entries()].map(([w, rules], k) => (
                <span key={w} data-testid={`winner-strip-group-${w}`} data-rules={rules.join(',')}>
                  {k > 0 && ' · '}
                  {name(w)} ({rules.map((r) => ruleLabels[r]).join(', ')})
                </span>
              ))}
            </>
          )}
        </span>
      )}
      {behavior !== 'sincere' && (
        <span className="text-xs text-muted-foreground">{t('strip.sincere')}</span>
      )}
    </div>
  );
};

export default WinnerStrip;
