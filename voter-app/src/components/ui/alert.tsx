import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

// Bootstrap-compatible Alert (Phase 6 Tailwind migration). Keeps the same
// `variant` names react-bootstrap uses (danger/success/warning/info/…) so the
// migration is a near drop-in: `<Alert variant="danger">msg</Alert>`. Renders a
// role="alert" div with the matching Bootstrap-ish colours.
const alertVariants = cva('rounded-md border px-3 py-2 text-sm', {
  variants: {
    variant: {
      primary: 'border-blue-300 bg-blue-100 text-blue-800',
      secondary: 'border-slate-300 bg-slate-100 text-slate-800',
      success: 'border-green-300 bg-green-100 text-green-800',
      danger: 'border-red-300 bg-red-100 text-red-800',
      warning: 'border-amber-300 bg-amber-100 text-amber-900',
      info: 'border-cyan-300 bg-cyan-100 text-cyan-900',
      light: 'border-slate-200 bg-slate-50 text-slate-800',
      dark: 'border-slate-700 bg-slate-800 text-slate-100',
    },
  },
  defaultVariants: { variant: 'primary' },
});

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant, ...props }, ref) => (
    <div ref={ref} role="alert" className={cn(alertVariants({ variant }), className)} {...props} />
  )
);
Alert.displayName = 'Alert';

export { Alert, alertVariants };
