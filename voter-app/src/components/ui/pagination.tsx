import * as React from 'react';

import { cn } from '@/lib/utils';

/** Bootstrap-compatible <Pagination> (+ .Item/.Prev/.Next/.First/.Last/.Ellipsis). */
const PaginationBase: React.FC<React.HTMLAttributes<HTMLUListElement> & { size?: 'sm' | 'lg' }> = ({
  className,
  size,
  ...props
}) => <ul className={cn('inline-flex items-center -space-x-px', className)} {...props} />;

export interface PageItemProps extends Omit<React.HTMLAttributes<HTMLLIElement>, 'onClick'> {
  active?: boolean;
  disabled?: boolean;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
}

const Item: React.FC<PageItemProps> = ({
  className,
  active,
  disabled,
  onClick,
  children,
  ...props
}) => (
  <li className={className} {...props}>
    <button
      type="button"
      disabled={disabled}
      aria-current={active ? 'page' : undefined}
      onClick={onClick}
      className={cn(
        'border border-border px-3 py-1.5 text-sm transition-colors first:rounded-l-md last:rounded-r-md',
        active
          ? 'z-10 border-primary bg-primary text-primary-foreground'
          : 'bg-background hover:bg-muted',
        disabled && 'pointer-events-none opacity-50'
      )}
    >
      {children}
    </button>
  </li>
);

const make = (label: React.ReactNode) => {
  const C: React.FC<PageItemProps> = (props) => <Item {...props}>{props.children ?? label}</Item>;
  return C;
};

const Ellipsis: React.FC<PageItemProps> = (props) => (
  <Item disabled {...props}>
    …
  </Item>
);

export const Pagination = Object.assign(PaginationBase, {
  Item,
  Prev: make('‹'),
  Next: make('›'),
  First: make('«'),
  Last: make('»'),
  Ellipsis,
});
