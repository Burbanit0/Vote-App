import * as React from 'react';
import { cn } from '@/lib/utils';

// Instrument — the app's signature framing for any graph/canvas. A hairline
// frame with corner registration ticks and a monospace label strip, so every
// visualisation reads as a panel on a scientific instrument rather than a
// generic card. Pair the label/readout (mono, the "data" voice) with an
// SVG/chart child.
//
// `variant="scope"` is the loud version for the Playground's central screen:
// stronger ticks, tinted telemetry strips, and an optional bottom `status`
// line — outputs read at the top, the configuration reads at the bottom, like a
// bench instrument. The default stays quiet for inline widgets (hero, campaign).

interface InstrumentProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Monospace eyebrow, e.g. "Trajectoire". */
  label?: React.ReactNode;
  /** Optional right-aligned monospace readout, e.g. a live value. */
  readout?: React.ReactNode;
  /** Optional bottom status strip (scope variant) — the standing configuration. */
  status?: React.ReactNode;
  /** Drop the inner padding (for edge-to-edge canvases). */
  flush?: boolean;
  variant?: 'default' | 'scope';
}

const Corner: React.FC<{ className: string; scope?: boolean }> = ({ className, scope }) => (
  <span
    aria-hidden
    className={cn(
      'pointer-events-none absolute',
      scope ? 'h-2.5 w-2.5 border-primary/55' : 'h-1.5 w-1.5 border-primary/40',
      className
    )}
  />
);

export const Instrument = React.forwardRef<HTMLDivElement, InstrumentProps>(
  ({ label, readout, status, flush, variant = 'default', className, children, ...props }, ref) => {
    const scope = variant === 'scope';
    const inset = scope ? 'left-1.5 top-1.5' : 'left-1 top-1';
    return (
      <div
        ref={ref}
        className={cn(
          'relative rounded-md border bg-card',
          scope ? 'border-primary/25 shadow-sm' : 'border-border',
          className
        )}
        {...props}
      >
        <Corner
          scope={scope}
          className={cn(inset.split(' ')[0], inset.split(' ')[1], 'border-l border-t')}
        />
        <Corner
          scope={scope}
          className={cn(scope ? 'right-1.5 top-1.5' : 'right-1 top-1', 'border-r border-t')}
        />
        <Corner
          scope={scope}
          className={cn(scope ? 'bottom-1.5 left-1.5' : 'bottom-1 left-1', 'border-b border-l')}
        />
        <Corner
          scope={scope}
          className={cn(scope ? 'bottom-1.5 right-1.5' : 'bottom-1 right-1', 'border-b border-r')}
        />

        {(label || readout) && (
          <div
            className={cn(
              'flex items-center justify-between gap-2 border-b px-3 py-1.5',
              scope ? 'border-primary/15 bg-muted/30' : 'border-border/70'
            )}
          >
            {label ? (
              <span
                className={cn(
                  'font-mono font-medium uppercase tracking-[0.14em] text-muted-foreground',
                  scope ? 'text-[0.6rem]' : 'text-[0.62rem]'
                )}
              >
                {label}
              </span>
            ) : (
              <span />
            )}
            {readout && (
              <span className="font-mono text-xs tabular-nums text-foreground">{readout}</span>
            )}
          </div>
        )}
        <div className={flush ? undefined : 'p-3'}>{children}</div>
        {status && (
          <div className="flex items-center gap-2 border-t border-primary/15 bg-muted/30 px-3 py-1.5 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-muted-foreground">
            {status}
          </div>
        )}
      </div>
    );
  }
);
Instrument.displayName = 'Instrument';
