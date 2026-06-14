import React, { useState } from 'react';

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
  children: React.ReactNode;
}

const Collapsible: React.FC<CollapsibleProps> = ({
  title,
  subtitle,
  defaultOpen = false,
  testid,
  onOpenChange,
  children,
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div data-testid={testid} className="rounded-md border border-border">
      <button
        type="button"
        data-testid={testid ? `${testid}-toggle` : undefined}
        aria-expanded={open}
        onClick={() =>
          setOpen((o) => {
            onOpenChange?.(!o);
            return !o;
          })
        }
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm font-medium hover:bg-accent/50"
      >
        <span className="flex items-center gap-2">
          <span
            className="text-muted-foreground transition-transform"
            style={{ transform: open ? 'rotate(90deg)' : 'none' }}
          >
            ▸
          </span>
          {title}
        </span>
        {subtitle && !open && (
          <span className="truncate text-xs font-normal text-muted-foreground/70">{subtitle}</span>
        )}
      </button>
      {open && <div className="border-t border-border p-3">{children}</div>}
    </div>
  );
};

export default Collapsible;
