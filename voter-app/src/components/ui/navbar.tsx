import * as React from 'react';

import { cn } from '@/lib/utils';

/**
 * Minimal Bootstrap-compatible <Navbar> (+ .Brand/.Toggle/.Collapse) and <Nav>
 * (+ .Link), enough for the app's single top navbar. `expand="lg"` is assumed:
 * the toggle shows below lg, the collapse is a flex row at lg+.
 */
interface NavbarCtx {
  expanded: boolean;
  setExpanded: (b: boolean) => void;
}
const NavbarContext = React.createContext<NavbarCtx>({ expanded: false, setExpanded: () => {} });

export interface NavbarProps extends Omit<React.HTMLAttributes<HTMLElement>, 'onToggle'> {
  expand?: boolean | 'sm' | 'md' | 'lg' | 'xl';
  expanded?: boolean;
  onToggle?: (next: boolean) => void;
  sticky?: 'top' | 'bottom';
  bg?: string;
  variant?: 'light' | 'dark';
}

const NavbarBase: React.FC<NavbarProps> = ({
  expand,
  expanded,
  onToggle,
  sticky,
  bg,
  variant,
  className,
  children,
  ...props
}) => {
  const [internal, setInternal] = React.useState(false);
  const exp = expanded !== undefined ? expanded : internal;
  const setExpanded = (b: boolean) => {
    if (expanded === undefined) setInternal(b);
    onToggle?.(b);
  };
  return (
    <NavbarContext.Provider value={{ expanded: exp, setExpanded }}>
      <nav
        className={cn(
          'relative flex flex-wrap items-center py-2',
          sticky === 'top' && 'sticky top-0 z-[1020]',
          sticky === 'bottom' && 'sticky bottom-0 z-[1020]',
          className
        )}
        {...props}
      >
        {children}
      </nav>
    </NavbarContext.Provider>
  );
};

const Brand: React.FC<React.AnchorHTMLAttributes<HTMLAnchorElement>> = ({
  className,
  ...props
}) => (
  <a
    className={cn('inline-flex items-center text-lg font-bold no-underline', className)}
    {...props}
  />
);

const Toggle: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement>> = ({
  className,
  ...props
}) => {
  const { expanded, setExpanded } = React.useContext(NavbarContext);
  return (
    <button
      type="button"
      onClick={() => setExpanded(!expanded)}
      className={cn(
        'ml-auto rounded border border-border px-2 py-1 text-xl leading-none lg:hidden',
        className
      )}
      {...props}
    >
      ☰
    </button>
  );
};

const Collapse: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => {
  const { expanded } = React.useContext(NavbarContext);
  return (
    <div
      className={cn(
        'grow basis-full items-center lg:flex lg:basis-auto',
        expanded ? 'flex flex-col lg:flex-row' : 'hidden',
        className
      )}
      {...props}
    />
  );
};

export const Navbar = Object.assign(NavbarBase, { Brand, Toggle, Collapse });

// ── Nav + Nav.Link ──────────────────────────────────────────────────────────
const NavBase: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => (
  <div className={cn('flex flex-col lg:flex-row', className)} {...props} />
);

export interface NavLinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  active?: boolean;
  disabled?: boolean;
  eventKey?: string;
}
const NavLink: React.FC<NavLinkProps> = ({ className, active, disabled, ...props }) => (
  <a
    className={cn(
      'block px-2 py-1 no-underline transition-colors',
      active ? 'font-semibold' : 'text-foreground/80 hover:text-foreground',
      disabled && 'pointer-events-none opacity-50',
      className
    )}
    {...props}
  />
);

export const Nav = Object.assign(NavBase, { Link: NavLink, Item: NavBase });
