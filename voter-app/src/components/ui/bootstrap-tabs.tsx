import * as React from 'react';

import { cn } from '@/lib/utils';

/**
 * Bootstrap-compatible <Tabs>/<Tab> (eventKey/title/activeKey/onSelect), so
 * react-bootstrap tab sets migrate by import-swap only. Renders a nav-tabs bar
 * plus the active panel. (Distinct from the shadcn radix Tabs in ./tabs.)
 */
export interface TabProps {
  eventKey: string;
  title: React.ReactNode;
  disabled?: boolean;
  tabClassName?: string;
  children?: React.ReactNode;
}

/** Marker component — actual rendering is handled by <Tabs>. */
export const Tab: React.FC<TabProps> = ({ children }) => <>{children}</>;
Tab.displayName = 'Tab';

export interface TabsProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  activeKey?: string;
  defaultActiveKey?: string;
  onSelect?: (key: string | null) => unknown;
  id?: string;
  mountOnEnter?: boolean;
  unmountOnExit?: boolean;
  justify?: boolean;
  fill?: boolean;
}

export const Tabs: React.FC<TabsProps> = ({
  activeKey,
  defaultActiveKey,
  onSelect,
  className,
  children,
  mountOnEnter,
  unmountOnExit,
  justify,
  fill,
  id,
  ...rest
}) => {
  const tabs = React.Children.toArray(children).filter(
    React.isValidElement
  ) as React.ReactElement<TabProps>[];
  const [internal, setInternal] = React.useState<string | undefined>(
    defaultActiveKey ?? tabs[0]?.props.eventKey
  );
  const active = activeKey !== undefined ? activeKey : internal;
  const select = (k: string) => {
    if (activeKey === undefined) setInternal(k);
    onSelect?.(k);
  };
  const activeTab = tabs.find((t) => t.props.eventKey === active);

  return (
    <div className={className} {...rest}>
      <div role="tablist" className="mb-3 flex flex-wrap gap-1 border-b border-border">
        {tabs.map((t) => {
          const isActive = t.props.eventKey === active;
          return (
            <button
              key={t.props.eventKey}
              role="tab"
              type="button"
              aria-selected={isActive}
              disabled={t.props.disabled}
              onClick={() => select(t.props.eventKey)}
              className={cn(
                '-mb-px cursor-pointer whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
                t.props.disabled && 'cursor-not-allowed opacity-50',
                t.props.tabClassName
              )}
            >
              {t.props.title}
            </button>
          );
        })}
      </div>
      <div role="tabpanel">{activeTab?.props.children}</div>
    </div>
  );
};
