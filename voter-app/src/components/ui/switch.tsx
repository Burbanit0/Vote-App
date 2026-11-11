import * as React from 'react';

import { cn } from '@/lib/utils';

/**
 * An on/off setting as a real switch: the whole row is the control (role="switch"),
 * its label on the left, a track on the right whose thumb slides across when on.
 */
export const Switch: React.FC<{
  checked: boolean;
  onChange: (checked: boolean) => void;
  children: React.ReactNode;
  testid?: string;
}> = ({ checked, onChange, children, testid }) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    data-testid={testid}
    onClick={() => onChange(!checked)}
    className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-[0.85rem] transition-colors hover:bg-muted"
  >
    <span className="flex items-center gap-2">{children}</span>
    <span
      aria-hidden="true"
      className={cn(
        'relative h-5 w-9 shrink-0 rounded-full transition-colors duration-200',
        checked ? 'bg-primary' : 'bg-muted-foreground/35'
      )}
    >
      <span
        className="absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-card shadow-sm transition-transform duration-200 ease-[cubic-bezier(.2,.7,.2,1)] motion-reduce:transition-none"
        style={{ transform: checked ? 'translateX(16px)' : 'none' }}
      />
    </span>
  </button>
);
