import * as React from 'react';
import { ChevronDown } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button, type ButtonProps } from '@/components/ui/button';

/**
 * Bootstrap-compatible <Dropdown> (+ .Toggle/.Menu/.Item/.Divider/.Header) and
 * <NavDropdown>, self-contained (open state + click-outside). Migrates the
 * react-bootstrap dropdowns by import-swap only.
 */
interface DdCtx {
  open: boolean;
  setOpen: (o: boolean) => void;
  rootRef: React.RefObject<HTMLDivElement | null>;
}
const DropdownContext = React.createContext<DdCtx | null>(null);

export interface DropdownProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  align?: 'start' | 'end';
  autoClose?: boolean | 'inside' | 'outside';
}

const DropdownBase: React.FC<DropdownProps> = ({ className, children, align, ...props }) => {
  const [open, setOpen] = React.useState(false);
  const rootRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);
  return (
    <DropdownContext.Provider value={{ open, setOpen, rootRef }}>
      <div ref={rootRef} className={cn('relative inline-block', className)} {...props}>
        {children}
      </div>
    </DropdownContext.Provider>
  );
};

const Toggle: React.FC<ButtonProps & { caret?: boolean }> = ({
  children,
  caret = true,
  ...props
}) => {
  const ctx = React.useContext(DropdownContext)!;
  return (
    <Button
      type="button"
      aria-expanded={ctx.open}
      onClick={() => ctx.setOpen(!ctx.open)}
      {...props}
    >
      {children}
      {caret && <ChevronDown className="ml-1 h-4 w-4" />}
    </Button>
  );
};

const Menu: React.FC<React.HTMLAttributes<HTMLDivElement> & { align?: 'start' | 'end' }> = ({
  className,
  children,
  align = 'start',
  ...props
}) => {
  const ctx = React.useContext(DropdownContext)!;
  if (!ctx.open) return null;
  return (
    <div
      role="menu"
      className={cn(
        'absolute z-[1000] mt-1 min-w-[10rem] rounded-md border border-border bg-popover p-1 text-popover-foreground shadow-md',
        align === 'end' ? 'right-0' : 'left-0',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export interface DropdownItemProps extends React.HTMLAttributes<HTMLElement> {
  active?: boolean;
  disabled?: boolean;
  href?: string;
  eventKey?: string;
}

const ITEM_CLASS =
  'block w-full cursor-pointer rounded-sm px-3 py-1.5 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground';

const Item: React.FC<DropdownItemProps> = ({
  className,
  active,
  disabled,
  onClick,
  children,
  href,
  eventKey,
  ...props
}) => {
  const ctx = React.useContext(DropdownContext)!;
  const classes = cn(
    ITEM_CLASS,
    active && 'bg-accent text-accent-foreground',
    disabled && 'pointer-events-none opacity-50',
    className
  );

  // react-bootstrap parity: an Item with `href` is a link, not a button.
  if (href && !disabled) {
    return (
      <a
        href={href}
        role="menuitem"
        onClick={(e) => {
          onClick?.(e);
          ctx.setOpen(false);
        }}
        className={cn(classes, 'no-underline')}
        {...props}
      >
        {children}
      </a>
    );
  }

  return (
    <button
      type="button"
      role="menuitem"
      disabled={disabled}
      onClick={(e) => {
        onClick?.(e);
        ctx.setOpen(false);
      }}
      className={classes}
      {...(props as React.ButtonHTMLAttributes<HTMLButtonElement>)}
    >
      {children}
    </button>
  );
};

const Divider: React.FC = () => <div className="my-1 h-px bg-border" />;
const HeaderEl: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => (
  <div
    className={cn('px-3 py-1.5 text-xs font-semibold text-muted-foreground', className)}
    {...props}
  />
);

export const Dropdown = Object.assign(DropdownBase, {
  Toggle,
  Menu,
  Item,
  Divider,
  Header: HeaderEl,
});

// ── NavDropdown (title + menu in one) ───────────────────────────────────────
export interface NavDropdownProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title: React.ReactNode;
  align?: 'start' | 'end';
  renderMenuOnMount?: boolean;
  menuVariant?: 'light' | 'dark';
}
const NavDropdownBase: React.FC<NavDropdownProps> = ({
  title,
  align,
  className,
  children,
  renderMenuOnMount,
  menuVariant,
  ...props
}) => (
  <DropdownBase className={className} {...props}>
    <Toggle variant="ghost" size="sm">
      {title}
    </Toggle>
    <Menu align={align}>{children}</Menu>
  </DropdownBase>
);
export const NavDropdown = Object.assign(NavDropdownBase, { Item, Divider, Header: HeaderEl });
