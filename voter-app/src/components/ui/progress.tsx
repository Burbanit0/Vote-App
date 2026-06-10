import * as React from 'react';

import { cn } from '@/lib/utils';

// Lightweight progress bar (Phase 6). Replaces react-bootstrap <ProgressBar
// now={n} max={m} variant=… />. `now`/`max` mirror that API; `variant` maps to
// the Bootstrap-ish fill colours.
const FILL: Record<string, string> = {
  primary: 'bg-primary',
  success: 'bg-[#198754]',
  danger: 'bg-[#dc3545]',
  warning: 'bg-[#ffc107]',
  info: 'bg-[#0dcaf0]',
  secondary: 'bg-slate-500',
};

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  now: number;
  max?: number;
  variant?: keyof typeof FILL;
  /** Show the percentage label inside the bar. */
  label?: React.ReactNode;
}

const Progress: React.FC<ProgressProps> = ({
  now,
  max = 100,
  variant = 'primary',
  label,
  className,
  ...props
}) => {
  const pct = max > 0 ? Math.min(100, Math.max(0, (now / max) * 100)) : 0;
  return (
    <div
      className={cn('h-4 w-full overflow-hidden rounded bg-muted', className)}
      role="progressbar"
      aria-valuenow={now}
      aria-valuemin={0}
      aria-valuemax={max}
      {...props}
    >
      <div
        className={cn(
          'flex h-full items-center justify-center text-xs text-white transition-[width]',
          FILL[variant]
        )}
        style={{ width: `${pct}%` }}
      >
        {label}
      </div>
    </div>
  );
};

export { Progress };
