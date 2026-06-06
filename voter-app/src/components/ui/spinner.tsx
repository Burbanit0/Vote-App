import * as React from 'react';
import { Loader2 } from 'lucide-react';

import { cn } from '@/lib/utils';

// Drop-in replacement for react-bootstrap <Spinner> (Phase 6). `size="sm"`
// mirrors the Bootstrap small spinner; otherwise a 1.5rem spinner.
export interface SpinnerProps extends React.HTMLAttributes<SVGSVGElement> {
  size?: 'sm' | 'md' | 'lg';
}

const SIZES = { sm: 'h-4 w-4', md: 'h-6 w-6', lg: 'h-8 w-8' } as const;

const Spinner: React.FC<SpinnerProps> = ({ size = 'md', className, ...props }) => (
  <Loader2
    className={cn('inline animate-spin', SIZES[size], className)}
    role="status"
    aria-label="loading"
    {...props}
  />
);

export { Spinner };
