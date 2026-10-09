import React from 'react';
import { useTranslation } from 'react-i18next';
import { useVotingLabels } from '../../hooks/useVotingLabels';
import { LEADER_RULES, hasFixedWinner, winnersByRule, groupByWinner } from '../../lib/scorecard';
import { candidateColor, textTone } from '../../lib/palette';
import { isSpatialSource } from '../../stores/useElectionStore';
import {
  useStoreCtx,
  useJourneyCtx,
  useInstrumentCtx,
  useScorecardCtx,
  useMethodSelection,
} from './PlaygroundController';
import NoFixedWinner from './NoFixedWinner';

/** Winner strip, above every moment: the map's rule and the winner the map shows
 * (strategic, when voters are), then what the other ticked methods elect on the same
 * expressed ballots, sincerely. Leader mode on a spatial electorate only: the
 * assembly's result is its seat chart, and a non-spatial profile's map lists the
 * backend's winners itself. */
const WinnerStrip: React.FC = () => {
  const { t } = useTranslation('playground');
  const { ruleLabels } = useVotingLabels();
  const { mode, behavior, prefSource } = useStoreCtx();
  const { leaderRule } = useJourneyCtx();
  const { expressedVoters, leaderCandidates } = useInstrumentCtx();
  const { strategicOutcome } = useScorecardCtx();
  const { enabledRules } = useMethodSelection();
  const shown = mode === 'leader' && isSpatialSource(prefSource);

  const otherRules = React.useMemo(
    () => LEADER_RULES.filter((r) => r !== leaderRule && hasFixedWinner(r) && enabledRules.has(r)),
    [leaderRule, enabledRules]
  );
  const winners = React.useMemo(
    () =>
      shown ? winnersByRule(expressedVoters, leaderCandidates, [leaderRule, ...otherRules]) : {},
    [shown, expressedVoters, leaderCandidates, leaderRule, otherRules]
  );

  const sincere = winners[leaderRule];
  if (!shown || (sincere == null && hasFixedWinner(leaderRule))) return null;
  // The map's readout shows the strategic winner when voters are strategic; mirror it.
  const current =
    behavior !== 'sincere' && strategicOutcome ? strategicOutcome.strategicWinner : sincere;
  const groups = groupByWinner(winners, otherRules);
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
        {hasFixedWinner(leaderRule) && current != null ? name(current) : <NoFixedWinner />}
      </span>
      {otherRules.length > 0 && (
        <span
          data-testid="winner-strip-others"
          data-rules={otherRules.join(',')}
          className="text-muted-foreground"
        >
          {groups.length === 1 && groups[0][0] === current ? (
            t('strip.othersAgree', { count: otherRules.length })
          ) : (
            <>
              {t('strip.othersElect')}{' '}
              {groups.map(([w, rules], k) => (
                <span key={w} data-testid={`winner-strip-group-${w}`} data-rules={rules.join(',')}>
                  {k > 0 && ' · '}
                  {name(w)} ({rules.map((r) => ruleLabels[r]).join(', ')})
                </span>
              ))}
            </>
          )}
          {behavior !== 'sincere' && ` ${t('strip.sincere')}`}
        </span>
      )}
    </div>
  );
};

export default WinnerStrip;
