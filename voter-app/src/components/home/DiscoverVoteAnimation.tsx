import React from 'react';
import { useTranslation } from 'react-i18next';
import { RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { voteFrames, type Frame, type TallyFrame } from '../../lib/discoverVoteAnim';
import type { Rule } from '../../lib/playgroundVoting';

// DiscoverVoteAnimation — the /decouvrir "dépouillement". Instead of bars, each
// method is counted by hand: votes are tally strokes (bâtons groupés par cinq,
// le 5ᵉ en barre — how French ballots are actually counted). Fixed-width strokes
// mean a row's length still compares magnitudes, so the tally IS the bar. Frames
// come from discoverVoteAnim (computed from the same ballots); rows remount per
// frame so each sweeps in as if freshly counted, and a runoff sends the
// eliminated pile's strokes drifting up toward the survivor. Honours
// prefers-reduced-motion (jumps to the final still, no strokes in flight).

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

const Tally: React.FC<{ n: number; className?: string; migrating?: boolean; delayMs?: number }> = ({
  n,
  className,
  migrating,
  delayMs = 0,
}) => (
  <span
    className={cn(
      'flex items-center gap-1',
      migrating ? 'tally-migrate-anim' : 'tally-sweep-anim',
      className
    )}
    style={{ animationDelay: `${delayMs}ms` }}
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
  const prevFrame = idx > 0 ? frames[idx - 1] : null;
  // How many strokes a food held in the previous frame — the pile that migrates
  // when it's eliminated at the runoff.
  const prevValue = (food: number): number => {
    if (!prevFrame || prevFrame.kind !== 'tally') return 0;
    return prevFrame.bars.find((b) => b.food === food)?.value ?? 0;
  };

  return (
    <div className="mt-3">
      <p className="min-h-[2.5rem] text-sm leading-relaxed text-foreground">
        {t(frame.captionKey)}
      </p>

      {frame.kind === 'tally' ? (
        // Keyed by frame + play so every count sweeps in fresh (and a runoff's
        // transfer replays), rather than silently swapping strokes.
        <div key={`${playToken}-${idx}`} className="mt-3 flex flex-col gap-2.5">
          {(frame as TallyFrame).bars.map((b, row) => (
            <div key={b.food} className="flex min-h-6 items-center gap-2.5">
              <span
                className={cn(
                  'flex w-16 shrink-0 items-center gap-1 text-sm',
                  b.eliminated && 'text-muted-foreground line-through'
                )}
              >
                <span aria-hidden>{foods[b.food].emoji}</span>
                {foods[b.food].name}
              </span>
              <span className="relative flex h-6 flex-1 items-center overflow-visible text-primary">
                {b.value > 0 && !noMotion.current && <Tally n={b.value} delayMs={row * 90} />}
                {b.value > 0 && noMotion.current && (
                  <span className="flex items-center gap-1">
                    {gatesOf(b.value).map((k, i) => (
                      <Gate key={i} k={k} />
                    ))}
                  </span>
                )}
                {/* The eliminated pile drifts up toward the survivor above it. */}
                {b.eliminated && !noMotion.current && prevValue(b.food) > 0 && (
                  <Tally
                    n={prevValue(b.food)}
                    migrating
                    className="absolute left-0 text-muted-foreground"
                  />
                )}
              </span>
              <span className="w-6 text-right font-mono text-sm font-semibold tabular-nums text-foreground">
                {b.value}
              </span>
            </div>
          ))}
        </div>
      ) : (
        // Condorcet: the two options face off across a centre rule; the longer
        // tally wins. Keyed by frame so each newly revealed duel counts in.
        <div key={`${playToken}-${idx}`} className="mt-3 flex flex-col gap-3">
          {frame.duels.map((d, row) => (
            <div key={d.right} className="flex items-center gap-2">
              <span className="flex flex-1 items-center justify-end gap-1.5 text-primary">
                <span className="font-mono text-sm font-semibold tabular-nums">{d.leftVotes}</span>
                <Tally n={d.leftVotes} delayMs={row * 120} />
                <span aria-hidden className="text-base">
                  {foods[d.left].emoji}
                </span>
              </span>
              <span className="h-8 w-px shrink-0 bg-border" />
              <span className="flex flex-1 items-center gap-1.5 text-muted-foreground">
                <span aria-hidden className="text-base">
                  {foods[d.right].emoji}
                </span>
                <Tally n={d.rightVotes} delayMs={row * 120} />
                <span className="font-mono text-sm font-semibold tabular-nums">{d.rightVotes}</span>
              </span>
            </div>
          ))}
        </div>
      )}

      {frames.length > 1 && !noMotion.current && (
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
