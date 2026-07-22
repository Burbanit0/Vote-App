import React from 'react';
import { useTranslation } from 'react-i18next';
import type { NamedPt } from '../../lib/playgroundVoting';
import type { VoteTrace } from '../../lib/voteTrace';
import { CANDIDATE_COLORS_LIGHT } from '../../constants/chartColors';

// ReplayStage — the "what is being counted right now" visual: one bar per
// candidate for the current frame, the unit label, and the beat's caption.
// Purely presentational (state lives in useVoteReplay), so the replay modal and
// the side-by-side face-à-face render an identical count.

const color = (i: number) => CANDIDATE_COLORS_LIGHT[i % CANDIDATE_COLORS_LIGHT.length];

const ReplayStage: React.FC<{
  trace: VoteTrace;
  frame: number;
  candidates: NamedPt[];
  /** Tighter type + no unit line, for the cramped two-column duel. */
  compact?: boolean;
}> = ({ trace, frame, candidates, compact = false }) => {
  const { t } = useTranslation('playground');
  const cur = trace.frames[Math.min(frame, trace.frames.length - 1)];
  const scale = Math.max(1, ...trace.frames.flatMap((f) => f.bars));

  return (
    <>
      <div className="flex flex-col gap-1.5" data-testid="replay-bars">
        {candidates.map((c, i) => {
          const val = cur.bars[i] ?? 0;
          const dead = cur.eliminated?.[i];
          const lit = cur.highlight?.includes(i);
          return (
            <div
              key={c.name}
              className={`flex items-center gap-2 rounded px-1 py-0.5 transition-opacity ${
                dead ? 'opacity-35' : ''
              } ${lit ? 'bg-muted/60' : ''}`}
            >
              <span
                className={`${compact ? 'w-16' : 'w-24'} shrink-0 truncate ${
                  compact ? 'text-[0.7rem]' : 'text-xs'
                } ${lit ? 'font-semibold' : ''} ${dead ? 'line-through' : ''}`}
                style={{ color: color(i) }}
              >
                {c.name}
              </span>
              <div className="relative h-4 flex-1 overflow-hidden rounded bg-muted/40">
                <div
                  className="absolute inset-y-0 left-0 rounded transition-[width] duration-300 ease-out"
                  style={{ width: `${(val / scale) * 100}%`, background: color(i) }}
                />
              </div>
              <span className="w-10 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                {Math.round(val * 10) / 10}
              </span>
            </div>
          );
        })}
      </div>
      {!compact && <p className="text-[0.65rem] text-muted-foreground">{t(trace.unitKey)}</p>}

      <div
        data-testid="replay-caption"
        className={`min-h-[2.5rem] rounded-md border border-border bg-muted/30 px-3 py-2 ${
          compact ? 'text-xs' : 'text-sm'
        }`}
      >
        {t(cur.caption.key, cur.caption.params)}
      </div>
    </>
  );
};

export default ReplayStage;
