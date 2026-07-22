import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { RotateCcw, Shuffle } from 'lucide-react';
import { usePlaygroundCtx } from '../playground/PlaygroundController';
import { useVotingLabels } from '../../hooks/useVotingLabels';
import { useVoteReplay, SPEEDS } from '../../hooks/useVoteReplay';
import ReplayStage from '../playground/ReplayStage';
import { LEADER_RULES, EXTRA_RULES } from '../../lib/scorecard';
import { sampleVoters } from '../../lib/voteTrace';
import { ruleWinner, type Rule, type Pt, type NamedPt } from '../../lib/playgroundVoting';
import { CANDIDATE_COLORS_LIGHT } from '../../constants/chartColors';

// MethodDuel — the face-à-face. Two voting methods, each on its OWN rule but the
// SAME sampled ballots, counted side by side so the app's thesis is literal: does
// the winner depend on the method? The winner shown is the engine's verdict on the
// shared sample (so it agrees with the dépouillement animating below it), and the
// verdict line names whether the two methods agree.

const candColor = (i: number) => CANDIDATE_COLORS_LIGHT[i % CANDIDATE_COLORS_LIGHT.length];

const RuleSelect: React.FC<{
  value: Rule;
  onChange: (r: Rule) => void;
  testid: string;
  labels: Record<string, string>;
}> = ({ value, onChange, testid, labels }) => {
  const { t } = useTranslation('playground');
  return (
    <select
      data-testid={testid}
      className="min-w-0 flex-1 rounded-md border border-input bg-background px-2 py-1 text-sm font-semibold"
      value={value}
      onChange={(e) => onChange(e.target.value as Rule)}
    >
      <optgroup label={t('replay.groupCompared')}>
        {LEADER_RULES.map((r) => (
          <option key={r} value={r}>
            {labels[r]}
          </option>
        ))}
      </optgroup>
      <optgroup label={t('replay.groupExtra')}>
        {EXTRA_RULES.map((r) => (
          <option key={r} value={r}>
            {labels[r]}
          </option>
        ))}
      </optgroup>
    </select>
  );
};

const DuelSide: React.FC<{
  side: 'a' | 'b';
  voters: Pt[];
  candidates: NamedPt[];
  rule: Rule;
  onRule: (r: Rule) => void;
  winnerIdx: number;
  seed: number;
  speedIdx: number;
  playToken: number;
  labels: Record<string, string>;
}> = ({ side, voters, candidates, rule, onRule, winnerIdx, seed, speedIdx, playToken, labels }) => {
  const { t } = useTranslation('playground');
  const { trace, frame } = useVoteReplay(voters, candidates, rule, {
    speedIdx,
    seed,
    restartKey: playToken,
  });
  const winner = winnerIdx >= 0 ? candidates[winnerIdx] : null;

  return (
    <div
      data-testid={`duel-side-${side}`}
      className="flex min-w-0 flex-col gap-2 rounded-lg border border-border bg-card p-3"
    >
      <div className="flex items-center gap-2">
        <RuleSelect value={rule} onChange={onRule} testid={`duel-rule-${side}`} labels={labels} />
      </div>

      <div className="flex items-center gap-2">
        <span className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-muted-foreground">
          {t('duel.winner')}
        </span>
        {winner ? (
          <span
            data-testid={`duel-winner-${side}`}
            className="rounded border px-1.5 py-0.5 font-mono text-xs font-bold"
            style={{
              color: candColor(winnerIdx),
              borderColor: `${candColor(winnerIdx)}55`,
              background: `${candColor(winnerIdx)}12`,
            }}
          >
            {winner.name}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </div>

      {trace ? (
        <ReplayStage trace={trace} frame={frame} candidates={candidates} compact />
      ) : (
        <p className="py-6 text-center text-xs text-muted-foreground">{t('duel.needCandidates')}</p>
      )}
    </div>
  );
};

const MethodDuel: React.FC = () => {
  const { t } = useTranslation('playground');
  const { ruleLabels } = useVotingLabels();
  const { votingVoters, leaderCandidates } = usePlaygroundCtx();

  const [left, setLeft] = useState<Rule>('plurality');
  const [right, setRight] = useState<Rule>('condorcet');
  const [seed, setSeed] = useState(1);
  const [speedIdx, setSpeedIdx] = useState(1); // normal
  const [playToken, setPlayToken] = useState(0);

  // The two sides count the SAME sampled ballots (deterministic in seed+size), so
  // the comparison is honest — only the rule differs. Winners come from that exact
  // sample, so they match the animation each side plays out.
  const sample = useMemo(
    () => sampleVoters(votingVoters, SPEEDS[speedIdx].n, seed),
    [votingVoters, speedIdx, seed]
  );
  const ready = sample.length > 0 && leaderCandidates.length >= 2;
  const winA = useMemo(
    () => (ready ? ruleWinner(sample, leaderCandidates, left) : -1),
    [ready, sample, leaderCandidates, left]
  );
  const winB = useMemo(
    () => (ready ? ruleWinner(sample, leaderCandidates, right) : -1),
    [ready, sample, leaderCandidates, right]
  );
  const differ = winA >= 0 && winB >= 0 && winA !== winB;

  return (
    <section className="flex flex-col gap-3">
      <div>
        <p className="font-mono text-[0.62rem] uppercase tracking-[0.2em] text-primary">
          {t('duel.eyebrow')}
        </p>
        <h2 className="font-display text-lg font-bold tracking-tight">{t('duel.title')}</h2>
        <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">{t('duel.intro')}</p>
      </div>

      {/* Verdict — the thesis, made literal for the current pairing. */}
      <div
        data-testid="duel-verdict"
        className={`rounded-md border px-3 py-2 text-sm ${
          differ
            ? 'border-[var(--color-stamp)]/50 bg-[var(--color-stamp)]/5 text-foreground'
            : 'border-border bg-muted/20 text-muted-foreground'
        }`}
      >
        {ready
          ? differ
            ? t('duel.verdictDiffer', {
                a: leaderCandidates[winA]?.name,
                b: leaderCandidates[winB]?.name,
              })
            : t('duel.verdictSame', { name: leaderCandidates[winA]?.name ?? '—' })
          : t('duel.needCandidates')}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <DuelSide
          side="a"
          voters={votingVoters}
          candidates={leaderCandidates}
          rule={left}
          onRule={setLeft}
          winnerIdx={winA}
          seed={seed}
          speedIdx={speedIdx}
          playToken={playToken}
          labels={ruleLabels}
        />
        <DuelSide
          side="b"
          voters={votingVoters}
          candidates={leaderCandidates}
          rule={right}
          onRule={setRight}
          winnerIdx={winB}
          seed={seed}
          speedIdx={speedIdx}
          playToken={playToken}
          labels={ruleLabels}
        />
      </div>

      {/* Shared clock — both sides count the same ballots, so they share controls. */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          data-testid="duel-replay"
          onClick={() => setPlayToken((n) => n + 1)}
          className="inline-flex items-center gap-1.5 rounded-md border border-primary px-2.5 py-1 text-xs font-semibold text-primary hover:bg-primary/10"
        >
          <RotateCcw className="h-3.5 w-3.5" /> {t('duel.replayBoth')}
        </button>
        <button
          type="button"
          data-testid="duel-reshuffle"
          onClick={() => setSeed((s) => s + 1)}
          className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs hover:bg-accent"
        >
          <Shuffle className="h-3.5 w-3.5" /> {t('replay.reshuffle')}
        </button>
        <div className="ml-auto flex items-center gap-1 text-xs">
          <span className="text-muted-foreground">{t('replay.speed')}</span>
          {SPEEDS.map((s, i) => (
            <button
              key={s.key}
              type="button"
              data-testid={`duel-speed-${s.key}`}
              onClick={() => setSpeedIdx(i)}
              className={`rounded border px-2 py-0.5 ${
                i === speedIdx
                  ? 'border-primary text-primary'
                  : 'border-border text-muted-foreground'
              }`}
            >
              {t(`replay.speed_${s.key}`)}
            </button>
          ))}
        </div>
      </div>

      <p className="text-[0.7rem] text-muted-foreground">
        {t('replay.sampleNote', { count: sample.length })}
      </p>
    </section>
  );
};

export default MethodDuel;
