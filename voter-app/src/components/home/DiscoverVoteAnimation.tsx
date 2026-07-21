import React from 'react';
import { useTranslation } from 'react-i18next';
import { RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { voteFrames, ELECTORATE, type Frame } from '../../lib/discoverVoteAnim';
import type { Rule } from '../../lib/playgroundVoting';

// DiscoverVoteAnimation — plays out HOW a method counts, so the /decouvrir demo
// shows the difference between rules instead of just flipping a winner. Frames
// come from discoverVoteAnim (computed from the same ballots); this component
// only tweens between them: bar widths grow, a two-round transfer slides Thaï's
// voters onto Sushi, and Condorcet reveals the head-to-head duels one by one.
// Honours prefers-reduced-motion by jumping straight to the final still.

interface Food {
  emoji: string;
  name: string;
}
const STEP_MS = 1400;

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;

const DiscoverVoteAnimation: React.FC<{
  rule: Rule;
  foods: readonly Food[];
  /** Approval only: how many options each voter approves. Sliding it re-tallies. */
  approvalK?: number;
}> = ({ rule, foods, approvalK = 2 }) => {
  const { t } = useTranslation();
  const frames = React.useMemo(() => voteFrames(rule, approvalK), [rule, approvalK]);
  const [idx, setIdx] = React.useState(0);
  const [grown, setGrown] = React.useState(false);
  // Bumping this replays the current method from the first frame.
  const [playToken, setPlayToken] = React.useState(0);
  const noMotion = React.useRef(prefersReducedMotion());

  React.useEffect(() => {
    if (noMotion.current) {
      setIdx(frames.length - 1);
      setGrown(true);
      return;
    }
    setIdx(0);
    setGrown(false);
    const raf = requestAnimationFrame(() => setGrown(true));
    const timers = frames
      .slice(1)
      .map((_, i) => window.setTimeout(() => setIdx(i + 1), (i + 1) * STEP_MS));
    return () => {
      cancelAnimationFrame(raf);
      timers.forEach(clearTimeout);
    };
  }, [rule, playToken, frames]);

  const frame: Frame = frames[Math.min(idx, frames.length - 1)];
  const pct = (v: number) => (grown ? (v / ELECTORATE) * 100 : 0);
  const transition = noMotion.current ? undefined : 'width 700ms ease-out';

  return (
    <div className="mt-3">
      <p className="min-h-[2.5rem] text-sm leading-relaxed text-foreground">
        {t(frame.captionKey)}
      </p>

      {frame.kind === 'tally' ? (
        // Rows persist across frames so a value change tweens (the transfer),
        // rather than remounting as a fresh chart.
        <div className="mt-2 flex flex-col gap-2">
          {frame.bars.map((b) => (
            <div key={b.food} className="flex items-center gap-2">
              <span
                className={cn(
                  'flex w-20 shrink-0 items-center gap-1 text-sm',
                  b.eliminated && 'text-muted-foreground line-through'
                )}
              >
                <span aria-hidden>{foods[b.food].emoji}</span>
                {foods[b.food].name}
              </span>
              <div className="relative h-6 flex-1 overflow-hidden rounded bg-muted/40">
                <div
                  className={cn(
                    'h-full rounded',
                    b.eliminated ? 'bg-muted-foreground/40' : 'bg-primary'
                  )}
                  style={{ width: `${pct(b.value)}%`, transition }}
                />
              </div>
              <span className="w-6 text-right font-mono text-sm font-semibold tabular-nums">
                {b.value}
              </span>
            </div>
          ))}
        </div>
      ) : (
        // Duels remount per frame so each newly revealed one grows from centre.
        <div key={idx} className="mt-2 flex flex-col gap-2">
          {frame.duels.map((d) => (
            <div
              key={d.right}
              className="flex h-8 overflow-hidden rounded border border-border text-sm font-semibold"
            >
              <div
                className="flex items-center justify-start gap-1 bg-primary px-2 text-primary-foreground"
                style={{ width: `${pct(d.leftVotes)}%`, transition }}
              >
                <span aria-hidden>{foods[d.left].emoji}</span>
                {d.leftVotes}
              </div>
              <div
                className="flex flex-1 items-center justify-end gap-1 bg-muted/60 px-2 text-muted-foreground"
                style={{ transition }}
              >
                {d.rightVotes}
                <span aria-hidden>{foods[d.right].emoji}</span>
              </div>
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
