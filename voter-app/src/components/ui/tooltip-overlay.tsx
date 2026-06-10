import * as React from 'react';

import { cn } from '@/lib/utils';

/**
 * Bootstrap-compatible <OverlayTrigger overlay={<Tooltip>…}> — a lightweight
 * hover/focus popover (no Popper). Enough for the tooltip use-cases in the app.
 */
export const Tooltip = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { id?: string }
>(({ className, children, ...props }, ref) => (
  <div
    ref={ref}
    role="tooltip"
    className={cn(
      'max-w-xs rounded bg-slate-900 px-2 py-1 text-xs text-white shadow-md',
      className
    )}
    {...props}
  >
    {children}
  </div>
));
Tooltip.displayName = 'Tooltip';

const PLACEMENT: Record<string, string> = {
  top: 'bottom-full left-1/2 mb-1 -translate-x-1/2',
  bottom: 'top-full left-1/2 mt-1 -translate-x-1/2',
  left: 'right-full top-1/2 mr-1 -translate-y-1/2',
  right: 'left-full top-1/2 ml-1 -translate-y-1/2',
};

export interface OverlayTriggerProps {
  overlay: React.ReactElement;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  children: React.ReactNode;
  /** Accepted for parity; ignored. */
  trigger?: unknown;
  delay?: unknown;
  show?: boolean;
}

export const OverlayTrigger: React.FC<OverlayTriggerProps> = ({
  overlay,
  placement = 'top',
  children,
}) => {
  const [show, setShow] = React.useState(false);
  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onFocus={() => setShow(true)}
      onBlur={() => setShow(false)}
    >
      {children}
      {show && (
        <span className={cn('absolute z-[1080] whitespace-nowrap', PLACEMENT[placement])}>
          {overlay}
        </span>
      )}
    </span>
  );
};
