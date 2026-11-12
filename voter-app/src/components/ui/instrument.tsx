import * as React from 'react';
import { cn } from '@/lib/utils';

// Instrument — the app's framing for any graph/canvas: a card with a label strip
// above the drawing (Bureau de vote: the label in the page's bold voice, the readout
// in mono, the "data" voice). Pair it with an SVG/chart child.
//
// `variant="scope"` is the Playground's central screen: a roomier strip with the
// label in petrol, and an optional bottom `status` line — outputs read at the top,
// the configuration at the bottom. The default stays quiet for inline widgets.

interface InstrumentProps extends React.HTMLAttributes<HTMLDivElement> {
  /** The strip's label, e.g. "Trajectoire". */
  label?: React.ReactNode;
  /** Optional right-aligned mono readout, e.g. a live value. */
  readout?: React.ReactNode;
  /** Optional bottom status strip (scope variant) — the standing configuration. */
  status?: React.ReactNode;
  /** Drop the inner padding (for edge-to-edge canvases). */
  flush?: boolean;
  variant?: 'default' | 'scope';
}

export const Instrument = React.forwardRef<HTMLDivElement, InstrumentProps>(
  ({ label, readout, status, flush, variant = 'default', className, children, ...props }, ref) => {
    const scope = variant === 'scope';
    return (
      <div
        ref={ref}
        className={cn(
          'relative overflow-hidden rounded-2xl border border-border bg-card',
          className
        )}
        {...props}
      >
        {(label || readout) && (
          <div
            className={cn(
              'flex items-center justify-between gap-2 border-b border-border',
              scope ? 'px-4 py-2.5' : 'px-3 py-2'
            )}
          >
            {label ? (
              <span
                className={cn(
                  'font-bold',
                  scope ? 'text-sm text-primary' : 'text-[0.8rem] text-muted-foreground'
                )}
              >
                {label}
              </span>
            ) : (
              <span />
            )}
            {readout && (
              <span className="font-mono text-sm tabular-nums text-foreground">{readout}</span>
            )}
          </div>
        )}
        <div className={flush ? undefined : 'p-3'}>{children}</div>
        {status && (
          <div className="flex items-center gap-2 border-t border-border bg-muted/40 px-4 py-2 text-sm font-bold text-muted-foreground">
            {status}
          </div>
        )}
      </div>
    );
  }
);
Instrument.displayName = 'Instrument';
