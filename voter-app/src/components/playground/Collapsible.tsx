import React, { useRef, useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

// Collapsible — the progressive-disclosure primitive that lets the playground
// gain depth without clutter: advanced modules ship collapsed and open on
// demand, so the canvas + scorecard stay the focus (vs the Lab's flat tabs).

export interface CollapsibleProps {
  title: string;
  /** Optional short hint shown next to the title when closed. */
  subtitle?: string;
  defaultOpen?: boolean;
  testid?: string;
  /** Notified whenever the open state changes (e.g. to reveal a linked overlay). */
  onOpenChange?: (open: boolean) => void;
  /** Fired once when the toggle is first hovered/focused — used to PRELOAD the
   * panel's lazy chunk so the click feels instant (no mount, just a warm cache). */
  onPrefetch?: () => void;
  children: React.ReactNode;
}

const Collapsible: React.FC<CollapsibleProps> = ({
  title,
  subtitle,
  defaultOpen = false,
  testid,
  onOpenChange,
  onPrefetch,
  children,
}) => {
  const [open, setOpen] = useState(defaultOpen);
  const prefetched = useRef(false);
  const prefetch = () => {
    if (prefetched.current) return;
    prefetched.current = true;
    onPrefetch?.();
  };
  return (
    <div
      data-testid={testid}
      className={cn(
        'overflow-hidden rounded-xl border bg-card transition-colors motion-reduce:transition-none',
        open ? 'border-primary/40' : 'border-border'
      )}
    >
      <button
        type="button"
        data-testid={testid ? `${testid}-toggle` : undefined}
        aria-expanded={open}
        onMouseEnter={onPrefetch ? prefetch : undefined}
        onFocus={onPrefetch ? prefetch : undefined}
        onClick={() =>
          setOpen((o) => {
            onOpenChange?.(!o);
            return !o;
          })
        }
        className={cn(
          'flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left text-[15px] font-semibold transition-colors motion-reduce:transition-none',
          open ? 'bg-muted/50' : 'hover:bg-muted/60'
        )}
      >
        <span className="flex items-center gap-2">
          <ChevronRight
            aria-hidden
            className={cn(
              'h-4 w-4 shrink-0 transition-transform motion-reduce:transition-none',
              open ? 'rotate-90 text-primary' : 'text-muted-foreground'
            )}
          />
          {title}
        </span>
        {subtitle && !open && (
          <span className="truncate text-sm font-normal text-muted-foreground">{subtitle}</span>
        )}
      </button>
      {open && <div className="border-t border-border p-4">{children}</div>}
    </div>
  );
};

export default Collapsible;
