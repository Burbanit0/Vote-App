import * as React from 'react';

import { cn } from '@/lib/utils';
import { Button, type ButtonProps } from '@/components/ui/button';

/**
 * <Dropdown> (+ .Toggle/.Menu), self-contained (open state + click-outside).
 */
interface DdCtx {
  open: boolean;
  setOpen: (o: boolean) => void;
}
const DropdownContext = React.createContext<DdCtx | null>(null);

const DropdownBase: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => {
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
    <DropdownContext.Provider value={{ open, setOpen }}>
      <div ref={rootRef} className={cn('relative inline-block', className)} {...props}>
        {children}
      </div>
    </DropdownContext.Provider>
  );
};

const Toggle: React.FC<ButtonProps> = (props) => {
  const ctx = React.useContext(DropdownContext)!;
  return (
    <Button
      type="button"
      aria-expanded={ctx.open}
      onClick={() => ctx.setOpen(!ctx.open)}
      {...props}
    />
  );
};

const Menu: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => {
  const ctx = React.useContext(DropdownContext)!;
  if (!ctx.open) return null;
  return (
    <div
      role="menu"
      className={cn(
        'absolute left-0 z-[1000] mt-1 min-w-[10rem] rounded-md border border-border bg-popover p-1 text-popover-foreground shadow-md',
        className
      )}
      {...props}
    />
  );
};

export const Dropdown = Object.assign(DropdownBase, { Toggle, Menu });
