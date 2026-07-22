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
        'overflow-hidden rounded-md border transition-colors',
        open ? 'border-primary/25' : 'border-border'
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
          'flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm font-medium transition-colors',
          open ? 'bg-muted/40' : 'hover:bg-accent/50'
        )}
      >
        <span className="flex items-center gap-2">
          <ChevronRight
            aria-hidden
            className={cn(
              'h-3.5 w-3.5 shrink-0 transition-transform',
              open ? 'rotate-90 text-primary' : 'text-muted-foreground'
            )}
          />
          {title}
        </span>
        {subtitle && !open && (
          <span className="truncate text-xs font-normal text-muted-foreground">{subtitle}</span>
        )}
      </button>
      {open && <div className="border-t border-primary/15 p-3">{children}</div>}
    </div>
  );
};

export default Collapsible;
