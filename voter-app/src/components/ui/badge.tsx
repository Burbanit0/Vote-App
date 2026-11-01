import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

// Canonical shadcn/ui Badge (+ Vote Lab `brand`/`success`/`warning` variants so
// the many Bootstrap `bg="success"`/`bg="primary"` badges map cleanly).
const badgeVariants = cva(
  'inline-flex items-center rounded-md border border-border px-2.5 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-transparent bg-muted text-muted-foreground',
        destructive: 'border-transparent bg-destructive text-destructive-foreground',
        outline: 'text-foreground',
        brand: 'border-transparent bg-brand text-white',
        // Bootstrap `bg=` aliases (migrate `<Badge bg="x">` → `variant="x"`).
        primary: 'border-transparent bg-primary text-primary-foreground',
        // Tinted, not filled: a badge is a label, the page's colour stays with the data.
        success: 'border-transparent bg-ok/15 text-ok',
        warning: 'border-transparent bg-stamp/20 text-foreground',
        info: 'border-transparent bg-primary/10 text-primary',
        danger: 'border-transparent bg-destructive/15 text-destructive',
        light: 'border-transparent bg-muted text-foreground',
        dark: 'border-transparent bg-foreground text-background',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge };
