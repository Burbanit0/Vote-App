import * as React from 'react';
import { cn } from '@/lib/utils';

// Instrument — the app's signature framing for any graph/canvas. A hairline
// frame with corner ticks and a monospace label strip, so every visualisation
// reads as a panel on a scientific instrument rather than a generic card.
// Pair the label/readout (mono, the "data" voice) with an SVG/chart child.

interface InstrumentProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Monospace eyebrow, e.g. "Trajectoire". */
  label?: React.ReactNode;
  /** Optional right-aligned monospace readout, e.g. a live value. */
  readout?: React.ReactNode;
  /** Drop the inner padding (for edge-to-edge canvases). */
  flush?: boolean;
}

const Corner: React.FC<{ className: string }> = ({ className }) => (
  <span
    aria-hidden
    className={cn('pointer-events-none absolute h-1.5 w-1.5 border-primary/40', className)}
  />
);

export const Instrument = React.forwardRef<HTMLDivElement, InstrumentProps>(
  ({ label, readout, flush, className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('relative rounded-md border border-border bg-card', className)}
      {...props}
    >
      <Corner className="left-1 top-1 border-l border-t" />
      <Corner className="right-1 top-1 border-r border-t" />
      <Corner className="bottom-1 left-1 border-b border-l" />
      <Corner className="bottom-1 right-1 border-b border-r" />

      {(label || readout) && (
        <div className="flex items-center justify-between gap-2 border-b border-border/70 px-3 py-1.5">
          {label ? (
            <span className="font-mono text-[0.62rem] font-medium uppercase tracking-[0.14em] text-muted-foreground">
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
    </div>
  )
);
Instrument.displayName = 'Instrument';

export default Instrument;
