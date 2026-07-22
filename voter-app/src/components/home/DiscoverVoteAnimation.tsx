import React from 'react';
import { RotateCcw, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { voteFrames, type Frame, type TallyFrame } from '../../lib/discoverVoteAnim';
import type { Rule } from '../../lib/playgroundVoting';

// DiscoverVoteAnimation — the /decouvrir "dépouillement". Instead of bars, each
// method is counted by hand: votes are tally strokes (bâtons groupés par cinq,
// le 5ᵉ en barre — how French ballots are actually counted). Fixed-width strokes
// mean a row's length still compares magnitudes, so the tally IS the bar. Frames
// come from discoverVoteAnim (computed from the same ballots).
//
// The move that carries the runoff: an eliminated pile does not blink to zero and
// re-appear as an abstract number. Its ballots travel into the survivor's pile and
// stay there marked in terracotta with the eliminated option's face — so the
// winning pile reads as "our ballots + the ones that came over," which is exactly
// what a redistribution is. The final frame flags the leading pile so "the biggest
// pile wins" is shown, not asserted. Honours prefers-reduced-motion (jumps to the
// final still, nothing in flight).

interface Food {
  emoji: string;
  name: string;
}
const STEP_MS = 1600;

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;

// A count as groups of five: 12 → [5,5,2].
const gatesOf = (n: number): number[] => {
  const g: number[] = [];
  let r = n;
  while (r >= 5) {
    g.push(5);
    r -= 5;
  }
  if (r > 0) g.push(r);
  return g;
};

// One tally gate: up to four uprights, the fifth a diagonal slash across them.
const Gate: React.FC<{ k: number }> = ({ k }) => {
  const xs = [3, 8, 13, 18];
  return (
    <svg
      viewBox="0 0 22 20"
      className="h-5 w-[22px] shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      aria-hidden
    >
      {xs.slice(0, Math.min(k, 4)).map((x, i) => (
        <line key={i} x1={x} y1={2.5} x2={x} y2={17.5} />
      ))}
      {k === 5 && <line x1={0.5} y1={17.5} x2={21} y2={2.5} />}
    </svg>
  );
};

// A run of strokes. Animated: sweeps in left-to-right (a hand laying them down);
// migrating: drifts off as the pile empties; still: the reduced-motion fallback.
const Strokes: React.FC<{
  n: number;
  animated: boolean;
  migrating?: boolean;
  delayMs?: number;
  className?: string;
}> = ({ n, animated, migrating, delayMs = 0, className }) => (
  <span
    className={cn(
      'flex items-center gap-1',
      animated && (migrating ? 'tally-migrate-anim' : 'tally-sweep-anim'),
      className
    )}
    style={animated ? { animationDelay: `${delayMs}ms` } : undefined}
  >
    {gatesOf(n).map((k, i) => (
      <Gate key={i} k={k} />
    ))}
  </span>
);

const DiscoverVoteAnimation: React.FC<{
  rule: Rule;
  foods: readonly Food[];
  /** Approval only: how many options each voter approves. Sliding it re-counts. */
  approvalK?: number;
}> = ({ rule, foods, approvalK = 2 }) => {
  const { t } = useTranslation();
  const frames = React.useMemo(() => voteFrames(rule, approvalK), [rule, approvalK]);
  const [idx, setIdx] = React.useState(0);
  // Bumping this replays the current method from the first frame.
  const [playToken, setPlayToken] = React.useState(0);
  const noMotion = React.useRef(prefersReducedMotion());
  const animate = !noMotion.current;

  React.useEffect(() => {
    if (noMotion.current) {
      setIdx(frames.length - 1);
      return;
    }
    setIdx(0);
    const timers = frames
      .slice(1)
      .map((_, i) => window.setTimeout(() => setIdx(i + 1), (i + 1) * STEP_MS));
    return () => timers.forEach(clearTimeout);
  }, [rule, playToken, frames]);

  const frame: Frame = frames[Math.min(idx, frames.length - 1)];
  const isLast = idx >= frames.length - 1;
  const prevFrame = idx > 0 ? frames[idx - 1] : null;
  // How many strokes a food held in the previous frame — the pile that leaves
  // when it's eliminated at the runoff.
  const prevValue = (food: number): number => {
    if (!prevFrame || prevFrame.kind !== 'tally') return 0;
    return prevFrame.bars.find((b) => b.food === food)?.value ?? 0;
  };

  // The leading pile of the final still — flagged so "the biggest pile wins" is
  // shown. A tie (e.g. approve-everyone) has no unique lead and stays unflagged.
  const leadFood = React.useMemo(() => {
    if (!isLast || frame.kind !== 'tally') return -1;
    const max = Math.max(...frame.bars.map((b) => b.value));
    const leaders = frame.bars.filter((b) => b.value === max);
    return leaders.length === 1 ? leaders[0].food : -1;
  }, [isLast, frame]);

  return (
    <div className="mt-3">
      <p className="min-h-[2.5rem] text-sm leading-relaxed text-foreground">
        {t(frame.captionKey)}
      </p>

      {frame.kind === 'tally' ? (
        // Keyed by frame + play so every count sweeps in fresh (and a runoff's
        // transfer replays), rather than silently swapping strokes.
        <div key={`${playToken}-${idx}`} className="mt-3 flex flex-col gap-1.5">
          {(frame as TallyFrame).bars.map((b, row) => {
            const own = b.value - (b.received ?? 0);
            const wins = b.food === leadFood;
            return (
              <div
                key={b.food}
                className={cn(
                  '-mx-1.5 flex min-h-7 items-center gap-2.5 rounded-md px-1.5 transition-colors',
                  wins && 'bg-primary/5'
                )}
              >
                <span
                  className={cn(
                    'flex w-16 shrink-0 items-center gap-1 text-sm',
                    b.eliminated && 'text-muted-foreground line-through',
                    wins && 'font-semibold'
                  )}
                >
                  <span aria-hidden>{foods[b.food].emoji}</span>
                  {foods[b.food].name}
                </span>

                <span className="relative flex h-6 flex-1 items-center gap-1.5 overflow-visible">
                  {own > 0 && (
                    <Strokes
                      n={own}
                      animated={animate}
                      delayMs={row * 90}
                      className="text-primary"
                    />
                  )}
                  {/* Ballots that came over from the eliminated option: terracotta,
                      tagged with its face, laid down after the pile's own strokes. */}
                  {b.received ? (
                    <span
                      className="flex items-center gap-1 text-[var(--color-stamp)]"
                      title={b.from != null ? foods[b.from].name : undefined}
                    >
                      {b.from != null && (
                        <span aria-hidden className="text-sm leading-none">
                          {foods[b.from].emoji}
                        </span>
                      )}
                      <Strokes n={b.received} animated={animate} delayMs={row * 90 + 560} />
                    </span>
                  ) : null}
                  {/* The eliminated pile drifts off as its ballots move away. */}
                  {b.eliminated && animate && prevValue(b.food) > 0 && (
                    <Strokes
                      n={prevValue(b.food)}
                      animated
                      migrating
                      className="absolute left-0 text-muted-foreground"
                    />
                  )}
                </span>

                {wins && <Check aria-hidden className="h-4 w-4 shrink-0 text-primary" />}
                <span
                  className={cn(
                    'w-6 text-right font-mono text-sm tabular-nums',
                    wins ? 'font-bold text-primary' : 'font-semibold text-foreground'
                  )}
                >
                  {b.value}
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        // Condorcet: the two options face off across a centre rule; the longer
        // tally wins, and the winning side is checked. Keyed by frame so each
        // newly revealed duel counts in.
        <div key={`${playToken}-${idx}`} className="mt-3 flex flex-col gap-3">
          {frame.duels.map((d, row) => {
            const leftWins = d.leftVotes > d.rightVotes;
            return (
              <div key={d.right} className="flex items-center gap-2">
                <span
                  className={cn(
                    'flex flex-1 items-center justify-end gap-1.5',
                    leftWins ? 'text-primary' : 'text-muted-foreground'
                  )}
                >
                  {leftWins && <Check aria-hidden className="h-3.5 w-3.5 shrink-0" />}
                  <span className="font-mono text-sm font-semibold tabular-nums">
                    {d.leftVotes}
                  </span>
                  <Strokes n={d.leftVotes} animated={animate} delayMs={row * 120} />
                  <span aria-hidden className="text-base">
                    {foods[d.left].emoji}
                  </span>
                </span>
                <span className="h-8 w-px shrink-0 bg-border" />
                <span
                  className={cn(
                    'flex flex-1 items-center gap-1.5',
                    leftWins ? 'text-muted-foreground' : 'text-primary'
                  )}
                >
                  <span aria-hidden className="text-base">
                    {foods[d.right].emoji}
                  </span>
                  <Strokes n={d.rightVotes} animated={animate} delayMs={row * 120} />
                  <span className="font-mono text-sm font-semibold tabular-nums">
                    {d.rightVotes}
                  </span>
                  {!leftWins && <Check aria-hidden className="h-3.5 w-3.5 shrink-0" />}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {frames.length > 1 && animate && (
        <button
          type="button"
          onClick={() => setPlayToken((n) => n + 1)}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-semibold text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
        >
          <RotateCcw aria-hidden className="h-3.5 w-3.5" />
          {t('discover.anim.replay')}
        </button>
      )}
    </div>
  );
};

export default DiscoverVoteAnimation;
