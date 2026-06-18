import React, { useRef } from 'react';
import { cn } from '@/lib/utils';

// InfoPopover — the shared ⓘ affordance: a small button that toggles a popover
// (closes on outside click, keyboard-accessible). Presentation only; callers
// supply the content. Used by MethodInfo and ScenarioInfo so the subtle, on-
// demand pedagogy looks and behaves identically everywhere.

interface Props {
  /** Stable id for test hooks: renders `info-<testid>` / `pop-<testid>`. */
  testid: string;
  ariaLabel: string;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
  children: React.ReactNode;
}

const POS: Record<NonNullable<Props['placement']>, string> = {
  top: 'bottom-full left-1/2 mb-2 -translate-x-1/2',
  bottom: 'top-full left-1/2 mt-2 -translate-x-1/2',
  left: 'right-full top-1/2 mr-2 -translate-y-1/2',
  right: 'left-full top-1/2 ml-2 -translate-y-1/2',
};

/** A labelled line for popover bodies: bold lead-in + muted body. */
export const InfoLine: React.FC<{ label: string; children: React.ReactNode }> = ({
  label,
  children,
}) => (
  <p className="mt-1.5 text-[0.72rem] leading-snug">
    <span className="font-semibold text-foreground">{label} </span>
    <span className="text-muted-foreground">{children}</span>
  </p>
);

const InfoPopover: React.FC<Props> = ({
  testid,
  ariaLabel,
  placement = 'top',
  className,
  children,
}) => {
  const [show, setShow] = React.useState(false);
  const wrapRef = useRef<HTMLSpanElement>(null);

  const handleClickOutside = React.useCallback((e: MouseEvent) => {
    if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setShow(false);
  }, []);
  React.useEffect(() => {
    if (show) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [show, handleClickOutside]);

  return (
    <span ref={wrapRef} className="relative inline-block" data-style="tailwind">
      <button
        type="button"
        className={cn(
          'inline-flex shrink-0 cursor-pointer items-center border-0 bg-transparent px-0.5 align-middle leading-none text-muted-foreground hover:text-foreground',
          className
        )}
        style={{ fontSize: '0.72rem' }}
        aria-label={ariaLabel}
        aria-expanded={show}
        onClick={(e) => {
          e.stopPropagation();
          setShow((s) => !s);
        }}
        data-testid={`info-${testid}`}
      >
        ⓘ
      </button>

      {show && (
        <div
          role="tooltip"
          data-testid={`pop-${testid}`}
          className={cn(
            'absolute z-[1060] w-[300px] max-w-[300px] rounded-md border border-border bg-popover p-3 text-popover-foreground shadow-lg',
            POS[placement]
          )}
        >
          {children}
        </div>
      )}
    </span>
  );
};

export default InfoPopover;
