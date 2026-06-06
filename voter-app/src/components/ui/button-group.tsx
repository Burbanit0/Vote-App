import * as React from 'react';

import { cn } from '@/lib/utils';

/** Bootstrap-compatible <ButtonGroup> — collapses inner button radii/borders. */
export interface ButtonGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  vertical?: boolean;
  size?: 'sm' | 'lg';
}

export const ButtonGroup = React.forwardRef<HTMLDivElement, ButtonGroupProps>(
  ({ className, vertical, size, ...props }, ref) => (
    <div
      ref={ref}
      role="group"
      className={cn(
        'inline-flex',
        vertical
          ? 'flex-col [&>*:not(:first-child)]:-mt-px [&>*:not(:first-child)]:rounded-t-none [&>*:not(:last-child)]:rounded-b-none'
          : '[&>*:not(:first-child)]:-ml-px [&>*:not(:first-child)]:rounded-l-none [&>*:not(:last-child)]:rounded-r-none',
        className
      )}
      {...props}
    />
  )
);
ButtonGroup.displayName = 'ButtonGroup';
