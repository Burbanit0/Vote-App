import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

// Bootstrap-compatible Alert (Phase 6 Tailwind migration). Keeps the same
// `variant` names react-bootstrap uses (danger/success/warning/info/…) so the
// migration is a near drop-in: `<Alert variant="danger">msg</Alert>`. Renders a
// role="alert" div, drawn as a note in the margin (Bureau de vote): ink on a faint
// tint, the variant said by the rule down its left side, in both themes.
const alertVariants = cva(
  'rounded-lg border-0 border-l-[3px] px-3.5 py-2.5 text-sm text-foreground',
  {
    variants: {
      variant: {
        primary: 'border-l-primary bg-primary/[0.07]',
        info: 'border-l-primary bg-primary/[0.07]',
        secondary: 'border-l-muted-foreground/50 bg-muted',
        light: 'border-l-border bg-muted/60',
        success: 'border-l-ok bg-ok/[0.08]',
        danger: 'border-l-destructive bg-destructive/[0.08]',
        warning: 'border-l-stamp bg-stamp/[0.1]',
        dark: 'border-l-primary bg-foreground text-background',
      },
    },
    defaultVariants: { variant: 'primary' },
  }
);

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof alertVariants> {}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant, children, ...props }, ref) => {
    return (
      <div ref={ref} role="alert" className={cn(alertVariants({ variant }), className)} {...props}>
        {children}
      </div>
    );
  }
);
Alert.displayName = 'Alert';

export { Alert };
