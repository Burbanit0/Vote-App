import * as React from 'react';

import { cn } from '@/lib/utils';

// Lightweight, drop-in replacements for react-bootstrap's Form.Range /
// Form.Select / Form.Check (Phase 6 Tailwind migration). They wrap the native
// elements so the migration of the 117 Form.Range / 98 Form.Select / 36
// Form.Check call sites is near-mechanical and keeps the same value/onChange API.

/** Form.Range → styled native <input type="range">. */
const Range = React.forwardRef<HTMLInputElement, React.ComponentProps<'input'>>(
  ({ className, ...props }, ref) => (
    <input
      type="range"
      ref={ref}
      className={cn('h-2 w-full cursor-pointer accent-primary', className)}
      {...props}
    />
  )
);
Range.displayName = 'Range';

/** Form.Select → styled native <select>. Pass <option>s as children. */
const Select = React.forwardRef<HTMLSelectElement, React.ComponentProps<'select'>>(
  ({ className, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      {...props}
    />
  )
);
Select.displayName = 'Select';

/** Form.Check → a checkbox (or radio) with an inline label. Mirrors the common
 *  `<Form.Check type="checkbox" label="…" checked onChange />` usage. */
export interface CheckProps extends Omit<React.ComponentProps<'input'>, 'type'> {
  label?: React.ReactNode;
  type?: 'checkbox' | 'radio' | 'switch';
  id?: string;
}

const Check = React.forwardRef<HTMLInputElement, CheckProps>(
  ({ className, label, type = 'checkbox', id, ...props }, ref) => {
    const inputType = type === 'switch' ? 'checkbox' : type;
    const autoId = React.useId();
    const inputId = id ?? autoId;
    return (
      <label htmlFor={inputId} className="inline-flex cursor-pointer items-center gap-2 text-sm">
        <input
          id={inputId}
          ref={ref}
          type={inputType}
          className={cn('h-4 w-4 cursor-pointer accent-primary', className)}
          {...props}
        />
        {label != null && <span>{label}</span>}
      </label>
    );
  }
);
Check.displayName = 'Check';

export { Range, Select, Check };
