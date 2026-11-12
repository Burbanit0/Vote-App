import React from 'react';
import { useTranslation } from 'react-i18next';
import { useVotingLabels } from '../../hooks/useVotingLabels';
import { LEADER_RULES, hasFixedWinner, winnersByRule, groupByWinner } from '../../lib/scorecard';
import { candidateColor, textTone } from '../../lib/palette';
import { computeRanks, computeScores } from '../../lib/playgroundVoting';
import { buildTraceFromBallots } from '../../lib/voteTrace';
import { explainWinner } from '../../lib/explainWinner';
import { nextFlip, type Flip, type WinnerMark } from '../../lib/winnerFlip';
import { isSpatialSource } from '../../stores/useElectionStore';
import {
  useStoreCtx,
  useJourneyCtx,
  useInstrumentCtx,
  useScorecardCtx,
  useMethodSelection,
} from './PlaygroundController';
import NoFixedWinner from './NoFixedWinner';
import LiveAnnouncement from '../shared/ui/LiveAnnouncement';

/** How long "the winner changed" stays up. */
const FLIP_VISIBLE_MS = 8000;

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
  // The expressed ballots, ranked and scored once: the winners and the reason below read the same.
  const ballots = React.useMemo(
    () =>
      shown
        ? {
            ranks: computeRanks(expressedVoters, leaderCandidates),
            scores: computeScores(expressedVoters, leaderCandidates),
          }
        : undefined,
    [shown, expressedVoters, leaderCandidates]
  );
  const winners = React.useMemo(
    () =>
      shown
        ? winnersByRule(expressedVoters, leaderCandidates, [leaderRule, ...otherRules], ballots)
        : {},
    [shown, expressedVoters, leaderCandidates, leaderRule, otherRules, ballots]
  );

  const sincere = winners[leaderRule];
  // The map's readout shows the strategic winner when voters are strategic; mirror it.
  const strategic = behavior !== 'sincere' && strategicOutcome != null;
  const current = strategic ? strategicOutcome.strategicWinner : sincere;
  const sincereName = sincere == null ? undefined : leaderCandidates[sincere]?.name;

  // Why the winner wins, in the words of the map's method. Sincere votes only: a strategic
  // winner is not the one these ballots elect, and a sentence about the sincere tally would
  // name the wrong reasons. (Keyed on the behaviour, not on the strategic result, which arrives
  // ~200 ms late: the sentence would show, then vanish.)
  const why = React.useMemo(() => {
    if (!ballots || behavior !== 'sincere' || sincere == null || !hasFixedWinner(leaderRule))
      return null;
    const trace = buildTraceFromBallots(
      leaderCandidates,
      ballots.ranks,
      ballots.scores,
      leaderRule
    );
    return explainWinner(trace, leaderCandidates);
  }, [ballots, behavior, sincere, leaderRule, leaderCandidates]);

  // "The winner changed": read off the sincere winner, under the same method and the same field
  // of candidates (see winnerFlip). Sincere votes only: the strategic result trails its inputs by
  // ~200 ms and, for that long, belongs to the previous method or candidates, so it would
  // announce changes nobody made. An effect, because it compares with the previous render.
  const namesKey = leaderCandidates.map((c) => c.name).join('\u0000');
  const mark: WinnerMark | null = React.useMemo(
    () =>
      sincereName === undefined || behavior !== 'sincere' || !hasFixedWinner(leaderRule)
        ? null
        : { rule: leaderRule, names: namesKey.split('\u0000'), winner: sincereName },
    [leaderRule, namesKey, sincereName, behavior]
  );
  const previous = React.useRef<WinnerMark | null>(null);
  const [flip, setFlip] = React.useState<Flip | null>(null);
  React.useEffect(() => {
    const before = previous.current;
    previous.current = mark;
    setFlip((f) => nextFlip(before, mark, f));
  }, [mark]);
  // A sentence about a drag made a minute ago is not news: it fades after a few seconds.
  React.useEffect(() => {
    if (flip === null) return;
    const id = setTimeout(() => setFlip(null), FLIP_VISIBLE_MS);
    return () => clearTimeout(id);
  }, [flip]);

  if (!shown || (sincere == null && hasFixedWinner(leaderRule))) return null;
  const groups = groupByWinner(winners, otherRules);
  // Names are text, not HTML: React escapes them, so i18next must not (PLAN_BEYOND_CI W3.3).
  const raw = { interpolation: { escapeValue: false } };
  const announceKey = strategic ? 'strip.announceStrategic' : 'strip.announce';
  const announced =
    hasFixedWinner(leaderRule) && current != null
      ? t(announceKey, {
          rule: ruleLabels[leaderRule],
          // The strategic outcome is async and can trail a removed candidate by a frame.
          name: leaderCandidates[current]?.name ?? '—',
          ...raw,
        })
      : t('strip.announceNone', { rule: ruleLabels[leaderRule], ...raw });
  // The winner is spoken once it settles; so is the change, which the sighted read below.
  const spoken = flip ? `${announced} ${t('strip.flip', { ...flip, ...raw })}` : announced;
  const name = (i: number) => (
    <strong style={{ color: textTone(candidateColor(i)) }}>{leaderCandidates[i]?.name}</strong>
  );

  return (
    <div
      data-testid="winner-strip"
      // In the envelope tray, as the homepage's result is: the winner rises in and is
      // stamped each time it changes (keyed on it, so a drag that keeps it moves nothing).
      className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-2xl bg-envelope px-5 py-3 text-sm"
    >
      <LiveAnnouncement testId="winner-announce" text={spoken} />
      <span data-testid="winner-strip-current" className="font-display text-[22px] leading-none">
        {t('strip.under', { rule: ruleLabels[leaderRule] })}{' '}
        {hasFixedWinner(leaderRule) && current != null ? (
          <span key={`${leaderRule}-${current}`} className="home-up inline-block">
            {name(current)}
          </span>
        ) : (
          <NoFixedWinner />
        )}
      </span>
      {hasFixedWinner(leaderRule) && current != null && (
        <span key={`${leaderRule}-${current}`} aria-hidden="true" className="relative">
          <span className="home-bleed absolute inset-0 rounded border-2 border-ballot-stamp" />
          <span className="home-stamp block rounded border-2 border-ballot-stamp px-2 pt-px pb-0.5 font-display text-[15px] leading-[1.2] font-extrabold tracking-[0.08em] text-ballot-stamp uppercase">
            {t('strip.stamp')}
          </span>
        </span>
      )}
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
      {why && (
        <p data-testid="winner-why" className="m-0 basis-full text-[0.8rem] text-muted-foreground">
          {t(why.key, { ...why.params, ...raw })}
        </p>
      )}
      {flip && (
        <p data-testid="winner-flip" className="m-0 basis-full text-[0.8rem] font-bold">
          {t('strip.flip', { ...flip, ...raw })}
        </p>
      )}
    </div>
  );
};

export default WinnerStrip;
