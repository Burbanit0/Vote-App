import * as React from 'react';

import { cn } from '@/lib/utils';

// The tally is the site's counting mark: votes counted by hand, four uprights then the
// fifth struck across them (bâtons groupés par cinq, how French ballots are counted).
// /decouvrir counts its piles with it; the loaders below draw it in a loop, so waiting
// for a result looks like the count going on.

/** Strokes in a full gate: four uprights and the strike. */
const GATE_STROKES = 5;

/** A count as gates of five: 12 → [5, 5, 2]. */
export const gatesOf = (n: number): number[] =>
  Array.from({ length: Math.ceil(n / GATE_STROKES) }, (_, i) =>
    Math.min(GATE_STROKES, n - i * GATE_STROKES)
  );

const UPRIGHTS = [3, 8, 13, 18];

export interface TallyGateProps extends Omit<React.SVGProps<SVGSVGElement>, 'ref' | 'k'> {
  /** Strokes drawn, 1–5: up to four uprights, the fifth the strike. */
  k: number;
  /** Extra props for stroke `i` (0–4): how a caller animates the drawing. */
  strokeProps?: (i: number) => React.SVGProps<SVGLineElement>;
}

/** One tally gate, drawn in currentColor. Decorative unless the caller gives it a role. */
export const TallyGate: React.FC<TallyGateProps> = ({
  k,
  strokeProps,
  className,
  strokeWidth = 2,
  ...rest
}) => (
  <svg
    viewBox="0 0 22 20"
    className={cn('shrink-0', className)}
    fill="none"
    stroke="currentColor"
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    aria-hidden
    {...rest}
  >
    {UPRIGHTS.slice(0, Math.min(k, 4)).map((x, i) => (
      <line key={i} x1={x} y1={2.5} x2={x} y2={17.5} {...strokeProps?.(i)} />
    ))}
    {k === GATE_STROKES && <line x1={0.5} y1={17.5} x2={21} y2={2.5} {...strokeProps?.(4)} />}
  </svg>
);

// ── The loop ────────────────────────────────────────────────────────────────
// One animation drives every stroke: `.tally-loop` runs the registered property
// `--tally-t` from 0 to 1 on the container, and each stroke derives its own draw from its
// index (`--i`) out of `--tally-n` (tailwind.css). So the count stays in order however
// many strokes there are, with no timer and no per-stroke keyframes. Reduced motion stops
// the loop on a complete, still count.

/** The ms one stroke takes to be drawn. */
const STROKE_STEP_MS = { gate: 150, row: 110 } as const;
/** The share of a cycle spent drawing; the rest holds the count, then fades it. */
const DRAW_SHARE = { gate: 0.6, row: 0.75 } as const;

const loopVars = (n: number, kind: keyof typeof STROKE_STEP_MS): React.CSSProperties =>
  ({
    '--tally-n': n,
    '--tally-draw': DRAW_SHARE[kind],
    '--tally-cycle': `${Math.round((n * STROKE_STEP_MS[kind]) / DRAW_SHARE[kind])}ms`,
  }) as React.CSSProperties;

const loopStroke =
  (offset: number) =>
  (i: number): React.SVGProps<SVGLineElement> => ({
    pathLength: 1,
    className: 'tally-loop-stroke',
    style: { '--i': offset + i } as React.CSSProperties,
  });

const SIZES = {
  sm: 'h-4 w-[18px]',
  md: 'h-6 w-[26px]',
  lg: 'h-8 w-[35px]',
} as const;

export interface TallySpinnerProps extends Omit<React.SVGProps<SVGSVGElement>, 'ref' | 'k'> {
  size?: keyof typeof SIZES;
}

/** The small loader: a single gate counted in a loop, sized like an icon. */
export const TallySpinner: React.FC<TallySpinnerProps> = ({
  size = 'md',
  className,
  style,
  ...props
}) => (
  <TallyGate
    k={GATE_STROKES}
    strokeProps={loopStroke(0)}
    strokeWidth={size === 'sm' ? 2.4 : 2}
    className={cn('tally-loop inline-block align-[-0.125em]', SIZES[size], className)}
    style={{ ...loopVars(GATE_STROKES, 'gate'), ...style }}
    role="status"
    aria-label="loading"
    aria-hidden={undefined}
    {...props}
  />
);

export interface TallyLoaderProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Shown beside the count: it is what the status announces. */
  label: React.ReactNode;
  /** Gates in the count: 3 by default (fifteen strokes). */
  gates?: number;
  'data-testid'?: string;
}

/** The block loader: a row of gates counted by hand, in a loop, beside its label. */
export const TallyLoader: React.FC<TallyLoaderProps> = ({
  label,
  gates = 3,
  className,
  ...rest
}) => (
  <div
    role="status"
    className={cn('flex items-center justify-center gap-3 text-muted-foreground', className)}
    {...rest}
  >
    <span
      className="tally-loop flex items-center gap-1 text-foreground/70"
      style={loopVars(gates * GATE_STROKES, 'row')}
      aria-hidden
    >
      {Array.from({ length: gates }, (_, g) => (
        <TallyGate
          key={g}
          k={GATE_STROKES}
          strokeProps={loopStroke(g * GATE_STROKES)}
          className="h-5 w-[22px]"
        />
      ))}
    </span>
    <span className="text-sm">{label}</span>
  </div>
);
