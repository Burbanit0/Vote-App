import React from 'react';
import { RotateCcw, Check, type LucideIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { TallyGate, gatesOf } from '@/components/ui/tally';
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
// stay there in the eliminated option's colour, with its icon — so the winning
// pile reads as "our ballots + the ones that came over," which is exactly
// what a redistribution is. The final frame flags the leading pile so "the biggest
// pile wins" is shown, not asserted. Honours prefers-reduced-motion (jumps to the
// final still, nothing in flight).

/** A restaurant: its icon and its colour, which its strokes are counted in. */
export interface Food {
  Icon: LucideIcon;
  name: string;
  color: string;
}
const STEP_MS = 1600;

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;

/** The pause between two strokes of the count, in ms. */
const STROKE_MS = 45;

// One tally gate (ui/tally.tsx). Animated, each stroke is drawn in turn from `delayMs`,
// as a hand counting would.
const Gate: React.FC<{ k: number; delayMs?: number }> = ({ k, delayMs }) => (
  <TallyGate
    k={k}
    className="h-5 w-[22px]"
    strokeProps={
      delayMs == null
        ? undefined
        : (i) => ({
            pathLength: 1,
            className: 'stroke-draw',
            style: { animationDelay: `${delayMs + i * STROKE_MS}ms` },
          })
    }
  />
);

// A run of strokes. Animated: drawn one by one (a hand laying them down); migrating:
// drifts off as the pile empties; still: the reduced-motion fallback.
export const Strokes: React.FC<{
  n: number;
  animated: boolean;
  migrating?: boolean;
  delayMs?: number;
  className?: string;
}> = ({ n, animated, migrating, delayMs = 0, className }) => (
  <span className={cn('flex items-center gap-1', migrating && 'tally-migrate-anim', className)}>
    {gatesOf(n).map((k, i) => (
      <Gate
        key={i}
        k={k}
        delayMs={animated && !migrating ? delayMs + i * 5 * STROKE_MS : undefined}
      />
    ))}
  </span>
);

export const FoodIcon: React.FC<{ food: Food }> = ({ food }) => (
  <food.Icon
    aria-hidden
    className="h-4 w-4 shrink-0"
    strokeWidth={1.75}
    style={{ color: food.color }}
  />
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
                  <FoodIcon food={foods[b.food]} />
                  {foods[b.food].name}
                </span>

                <span className="relative flex h-6 flex-1 items-center gap-1.5 overflow-visible">
                  {own > 0 && (
                    <span style={{ color: foods[b.food].color }}>
                      <Strokes n={own} animated={animate} delayMs={row * 90} />
                    </span>
                  )}
                  {/* Ballots that came over from the eliminated option keep its colour
                      and its icon, laid down after the pile's own strokes. */}
                  {b.received ? (
                    <span
                      className="flex items-center gap-1"
                      style={{ color: b.from != null ? foods[b.from].color : undefined }}
                      title={b.from != null ? foods[b.from].name : undefined}
                    >
                      {b.from != null && <FoodIcon food={foods[b.from]} />}
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
                {/* The total is written once its strokes are down. */}
                <span
                  className={cn(
                    'w-6 text-right font-mono text-sm tabular-nums',
                    animate && 'home-up',
                    wins ? 'font-bold text-primary' : 'font-semibold text-foreground'
                  )}
                  style={{
                    animationDelay: `${row * 90 + (b.received ? 560 + b.received * STROKE_MS : own * STROKE_MS)}ms`,
                  }}
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
                  <FoodIcon food={foods[d.left]} />
                </span>
                <span className="h-8 w-px shrink-0 bg-border" />
                <span
                  className={cn(
                    'flex flex-1 items-center gap-1.5',
                    leftWins ? 'text-muted-foreground' : 'text-primary'
                  )}
                >
                  <FoodIcon food={foods[d.right]} />
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
