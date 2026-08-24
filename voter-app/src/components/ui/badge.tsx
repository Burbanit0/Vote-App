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
        secondary: 'border-transparent bg-slate-500 text-white',
        destructive: 'border-transparent bg-destructive text-destructive-foreground',
        outline: 'text-foreground',
        brand: 'border-transparent bg-brand text-white',
        // Bootstrap `bg=` aliases (migrate `<Badge bg="x">` → `variant="x"`).
        primary: 'border-transparent bg-primary text-primary-foreground',
        success: 'border-transparent bg-[#198754] text-white',
        warning: 'border-transparent bg-[#ffc107] text-black',
        info: 'border-transparent bg-[#0dcaf0] text-black',
        danger: 'border-transparent bg-[#dc3545] text-white',
        light: 'border-transparent bg-slate-100 text-slate-900',
        dark: 'border-transparent bg-slate-800 text-white',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge };
