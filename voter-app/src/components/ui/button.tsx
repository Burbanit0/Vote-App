import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

// Canonical shadcn/ui Button (Phase 6 — Tailwind migration). Styling uses only
// utility classes + the design tokens from src/styles/tailwind.css, so it works
// without Tailwind preflight (which is disabled while Bootstrap coexists).
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',

        // ── Bootstrap-name aliases (Phase 6) so `variant="success"` etc.
        // migrate as a near drop-in across the 262 react-bootstrap <Button>s.
        primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
        success: 'bg-[#198754] text-white hover:bg-[#198754]/90',
        danger: 'bg-[#dc3545] text-white hover:bg-[#dc3545]/90',
        warning: 'bg-[#ffc107] text-black hover:bg-[#ffc107]/90',
        info: 'bg-[#0dcaf0] text-black hover:bg-[#0dcaf0]/90',
        dark: 'bg-slate-900 text-white hover:bg-slate-900/90',
        light: 'bg-slate-100 text-slate-900 hover:bg-slate-200',
        'outline-primary': 'border border-primary text-primary hover:bg-primary/10',
        'outline-secondary':
          'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        'outline-success': 'border border-[#198754] text-[#198754] hover:bg-[#198754]/10',
        'outline-danger': 'border border-[#dc3545] text-[#dc3545] hover:bg-[#dc3545]/10',
        'outline-warning': 'border border-[#ffc107] text-[#9a7400] hover:bg-[#ffc107]/10',
        'outline-info': 'border border-[#0dcaf0] text-[#0a93ad] hover:bg-[#0dcaf0]/10',
        'outline-dark': 'border border-slate-900 text-slate-900 hover:bg-slate-900/10',
        'outline-light': 'border border-slate-300 text-slate-100 hover:bg-white/10',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 rounded-md px-3 text-xs',
        lg: 'h-10 rounded-md px-8',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  }
);
Button.displayName = 'Button';

export { Button };
