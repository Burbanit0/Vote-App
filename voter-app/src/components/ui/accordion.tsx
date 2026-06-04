import * as React from 'react';
import { ChevronDown } from 'lucide-react';

import { cn } from '@/lib/utils';

/**
 * Bootstrap-compatible <Accordion> (+ .Item/.Header/.Body, eventKey based), so
 * react-bootstrap accordions migrate by import-swap only. Self-contained (no
 * radix dep): a context tracks the open key(s); `alwaysOpen` allows multiple.
 */
interface AccCtx {
  active: string[];
  toggle: (k: string) => void;
}
const AccordionContext = React.createContext<AccCtx>({ active: [], toggle: () => {} });
const ItemContext = React.createContext<string>('');

export interface AccordionProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  defaultActiveKey?: string | string[];
  activeKey?: string | string[];
  alwaysOpen?: boolean;
  flush?: boolean;
  onSelect?: (key: string | null) => void;
}

const AccordionBase: React.FC<AccordionProps> = ({
  defaultActiveKey,
  activeKey,
  alwaysOpen,
  flush,
  onSelect,
  className,
  children,
  ...props
}) => {
  const norm = (v?: string | string[]) => (v == null ? [] : Array.isArray(v) ? v : [v]);
  const [internal, setInternal] = React.useState<string[]>(norm(defaultActiveKey));
  const active = activeKey !== undefined ? norm(activeKey) : internal;
  const toggle = (k: string) => {
    const isOpen = active.includes(k);
    const next = isOpen ? active.filter((x) => x !== k) : alwaysOpen ? [...active, k] : [k];
    if (activeKey === undefined) setInternal(next);
    onSelect?.(isOpen ? null : k);
  };
  return (
    <AccordionContext.Provider value={{ active, toggle }}>
      <div className={cn('overflow-hidden rounded-md border border-border', flush && 'rounded-none border-0', className)} {...props}>
        {children}
      </div>
    </AccordionContext.Provider>
  );
};

const Item: React.FC<React.HTMLAttributes<HTMLDivElement> & { eventKey: string }> = ({
  eventKey,
  className,
  children,
  ...props
}) => (
  <ItemContext.Provider value={eventKey}>
    <div className={cn('border-b border-border last:border-b-0', className)} {...props}>
      {children}
    </div>
  </ItemContext.Provider>
);

const Header: React.FC<React.HTMLAttributes<HTMLElement>> = ({ className, children, ...props }) => {
  const { active, toggle } = React.useContext(AccordionContext);
  const eventKey = React.useContext(ItemContext);
  const isOpen = active.includes(eventKey);
  return (
    <h2 className="m-0">
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={() => toggle(eventKey)}
        className={cn(
          'flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-medium transition-colors hover:bg-muted/50',
          className
        )}
        {...props}
      >
        <span>{children}</span>
        <ChevronDown className={cn('h-4 w-4 shrink-0 transition-transform', isOpen && 'rotate-180')} />
      </button>
    </h2>
  );
};

const Body: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, children, ...props }) => {
  const { active } = React.useContext(AccordionContext);
  const eventKey = React.useContext(ItemContext);
  const isOpen = active.includes(eventKey);
  // Always mount (matches react-bootstrap's collapse DOM); just hide when closed.
  return (
    <div hidden={!isOpen} className={cn('px-4 py-3 text-sm', className)} {...props}>
      {children}
    </div>
  );
};

export const Accordion = Object.assign(AccordionBase, { Item, Header, Body });
